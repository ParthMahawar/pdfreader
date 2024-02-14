"""Obtain main-body text from PDFs with support for multi-column layouts.

This module parses PDFs, with a focus on academic papers, and returns the text
from their main body, while also ordering the output correctly with respect to
text layouts with multiple columns or variable-width text sections.

Note: 
	This documentation will often refer to lists of pdfplumber chars - these
	chars are represented by the library as a dictionary of 
		{"propertyName1": value1,
	 	"propertyName2": value2,
	 	...}

	Refer to the documentation at https://github.com/jsvine/pdfplumber for
	more info.
"""

import pdfplumber
import re
from itertools import groupby
from stop_words import get_stop_words
from collections import Counter
from sklearn.cluster import DBSCAN
import numpy as np

class PDFReader:
	"""Each instance of this class will handle one PDF with its own settings.

	Attributes:
		PDFPath (str): File path of PDF to be parsed
		remove_newlines (bool): If true, all newline characters from
			the parsed text will be removed, to get the text in one continuous
			block. Defaults to False.
		remove_wordbreaks (bool): If true, will remove newlines when the previous line
			ends on a '-' character, removing cases where a word is split across
			two lines. Defaults to True.
		summary_sentences (int): Default number of sentences in output summary. (Experimental)
		mainBodyThreshold (float): Defines what fraction of the text on a page
			a certain font size must comprise to be considered part of the output
			main body text. Defaults to 0.2 (i.e. 20% of text on the page).
		cluster_eps (float): Determines how much of a gap between text is tolerated
			while keeping the text in the same cluster. Increase this number if
			random text on the page is missing or out of place, and decrease it if
			text on multiple columns is not separated. Defaults to 13.
		column_eps (float): Determines how much of gap between text clusters is tolerated
			while keeping them in the same column of text. Increase this number if single
			columns are showing up with text out of order, or decrease them if columns
			are not separated. Defaults to 175.

	Note:
		The default values for the cluster_eps and column_eps attributes have been selected
		based on PDFs formatted as Letter/A4 sized paper. If the PDF is formatted as 
		a different size of paper, it's likely that these attributes will have to be
		scaled accordingly.

	"""
	def __init__(self, PDFPath: str, remove_newlines: bool = False, remove_wordbreaks: bool = True, summary_sentences: int = 15):
		"""Initializes PDF Reader object for given PDF.

		See PDFReader class docstring for more info on these attributes
		Args:
			PDFPath (str): Sets PDFPath attribute.
			remove_newlines (bool, optional): Sets remove_newlines attribute.
			remove_wordbreaks (bool, optional): Sets remove_wordbreaks attribute.
			summary_sentences (int, optional): Sets summary_sentences attribute.
		"""

		self.PDFPath = PDFPath;
		self.remove_newlines = remove_newlines;
		self.remove_wordbreaks = remove_wordbreaks;
		self.summary_sentences = summary_sentences;
		self.mainBodyThreshold = 0.2
		self.cluster_eps = 13
		self.column_eps = 175
	
	# Classifies all characters by their font size - other attributes can be used with some modifications
	def classifyByStyle(self, chars: list) -> dict[float, list]:
		"""Classifies pdfplumber characters based on their font size.

		Args:
			chars (list): A list of pdfplumber characters.

		Returns:
			dict[float, list]: A dictionary with keys for each font size, with
				the respective values being a list of the input characters that
				had the corresponding font size as their 'size' property.
		"""
		styleMap = {}

		for char in chars:
			if char["size"] in styleMap:
				styleMap[char["size"]].append(char)
			else:
				styleMap[char["size"]] = [char]

		return styleMap

	def filterByFontSize(self, chars: list, acceptableSizes: list[float]) -> list:
		"""Filters list of pdfplumber characters, keeping only certain font sizes.

		Args:
			chars (list): A list of pdfplumber characters.
			acceptableSizes (list[float]): A list of font sizes to keep.

		Returns:
			list: List of pdfplumber characters that had an acceptable
				'size' value.
		"""

		filtered = []

		for char in chars:
			if char["size"] in acceptableSizes:
				filtered.append(char)

		return filtered

	# Clusters pages by paragraph, then returns columns of paragraphs - splitting the page into chunks the way a person 
	# would read them in English(top to bottom, left to right)
	def clusterPage(self, pageChars: list, eps: int = None, columneps: int = None) -> list[list]:
		"""Returns columns of pdfplumber chars from input list.

		Using the DBSCAN method, this function uses the characters' x and y
		positions to cluster them, then uses the centroids of those clusters
		to classify them by which text column they belong to.

		Args:
			pageChars (list): A list of pdfplumber characters.
			eps (float, optional): Cluster epsilon. See cluster_eps attribute 
				in PDFReader class docstring for more details.
			columneps (float, optional): Column Epsilon. See column_eps
				attribute in PDFReader class docstring for more details.

		Returns:
			list[list]: A list of columns in the page, left to right. Each
				column is represented as a list of pdfplumber characters.
		"""

		if eps is None:
			eps = self.cluster_eps
		if columneps is None:
			columneps = self.column_eps
		charPoints = np.array([[char['x0'], char['y0']] for char in pageChars])
		
		clusters = DBSCAN(eps=eps).fit(charPoints).labels_
		

		for i in range(len(pageChars)):
			pageChars[i]['cluster'] = clusters[i]

		clusterlabels = np.unique(clusters)
		clusterlabels = clusterlabels[clusterlabels != -1]


		clusterCentroids = []

		for cl in clusterlabels:
			cindices = clusters == cl
			pointsInCluster = charPoints[cindices]

			clusterCentroid = np.mean(pointsInCluster, axis=0)
			clusterCentroids.append((cl, clusterCentroid))

		columns = []

		while clusterCentroids:
			topLeft = max(clusterCentroids, key = lambda x: x[1][1]-(x[1][0])**2)
			
			column = []
			clusterCentroids.remove(topLeft)

			for i in range(len(clusterCentroids)):
				xCoord = clusterCentroids[i][1][0]
				
				if xCoord - topLeft[1][0] < columneps:
					column.append(clusterCentroids[i])

			clusterCentroids = [c for c in clusterCentroids if c not in column]
			column = [topLeft] + column
			columns.append(column)

		columnsAndChars = []

		for column in columns:
			columnClusters = [c[0] for c in column]
			columnChars = [char for char in pageChars if (char['cluster'] in columnClusters)]
			columnsAndChars.append(columnChars)

		return columnsAndChars

	# Very simple summary algorithm, looking for most common words, then returning sentences with the most, most common words
	def summarize(self, num_sentences: int = None) -> str:
		"""Summarizes the pdf text using a rather simple algorithm.

		This is a very basic summarizer that may or may not give great results,
		relying on scoring words by how often they occur in the text, and then
		ranking sentences based on the total scores of the words in them, returning
		the highest ranking sentences in order of their appearance in the text.
		Works better for text that is a continuous block of text sentences without
		interruption by mathematical notation etc.

		Args:
			num_sentences(int, optional): Number of sentences in summary. Defaults
				to num_sentences attribute of instance.

		Returns:
			str: Summary of input text
		"""
		if num_sentences is None:
			num_sentences = self.num_sentences
		text = self.get_text()
		stopwords = get_stop_words('en')

		text = text.replace('\n', ' ')
		sentences = [s.strip() for s in text.split('.')]
		words = text.replace('.', ' ').split(' ')

		wordcounts = Counter(words)

		for sw in stopwords:
			del wordcounts[sw]

		del wordcounts['']
		del wordcounts[' ']

		sentenceScores = []
		for sentence in sentences:
			sentenceScores.append(0)
			for word in sentence.split(' '):
				sentenceScores[-1] += wordcounts[word]

		sentences = list(enumerate(sentences))
		sentences.sort(key = lambda x : sentenceScores[x[0]], reverse=True)
		sentences = sentences[:num_sentences]
		sentences.sort(key = lambda x : x[0])

		output = ""
		for sentence in sentences:
			output += sentence[1]
			output += ".\n"

		return output

	def get_text(self) -> str:
		"""Gets full main body text from PDF.

		Returns:
			str: Main Body of PDF, settings based on instance attributes.
		"""

		paper = pdfplumber.open(self.PDFPath)

		output = ""

		for page in paper.pages:
			pageChars = page.chars

			for char in pageChars:
				char["size"] = round(char["size"], 1)

			smap = self.classifyByStyle(pageChars)
			mainBodySizes = []
			for size, sizeChars in smap.items():
				if (len(sizeChars)/len(pageChars)) > self.mainBodyThreshold:
					mainBodySizes.append(size)

			pageChars = self.filterByFontSize(pageChars, mainBodySizes)

			columns = self.clusterPage(pageChars, eps = self.cluster_eps, columneps = self.column_eps)

			for column in columns:
				output += pdfplumber.utils.extract_text(column, x_tolerance = 1)
				output += "\n"

		if self.remove_wordbreaks:
			output = re.sub('-[\r\n]+', "", output)
		if self.remove_newlines:
			output = output.replace("\n", " ")

		return output

	def get_raw_chars(self) -> list:
		"""Obtain all the the pdfplumber char objects from the PDF.

		Returns:
			list: A list of all the pdfplumber char objects from the PDF as is.
		"""
		paper = pdfplumber.open(self.PDFPath)

		paperChars = []

		for page in paper.pages:
			paperChars += page.chars

		return paperChars

	def write_to_text_file(self, textFilePath: str):
		"""Write text from PDF to a file.

		Args:
			textFilePath (str): Path of file to be written.
		"""
		output = self.get_text()
		with open(textFilePath, 'wb') as f:
			f.write(output.encode('utf8'))

if __name__ == "__main__":
	paperPath = "samples/testpaper1.pdf"
	print_result = True
	remove_newlines = False
	remove_wordbreaks = True # If remove_newlines is False, setting this to true will merge words split across two lines with a - (also removing that line break)
	print_summary = True
	summary_sentences = 15 # Number of sentences in summary
	write_to_text_file = False

	reader = PDFReader(PDFPath = paperPath, remove_newlines = False, remove_wordbreaks = True, summary_sentences = summary_sentences)

	if print_result:
		print(reader.get_text())
	if print_summary:
		print('------------------------')
		print('SUMMARY')
		print(reader.summarize(summary_sentences))

	if write_to_text_file:
		reader.write_to_text_file(paperPath.replace('.pdf', '.txt'))