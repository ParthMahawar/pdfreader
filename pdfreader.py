import pdfplumber
import re
from itertools import groupby
from stop_words import get_stop_words
from collections import Counter
from sklearn.cluster import DBSCAN
import numpy as np

paperPath = ""

print_result = True
remove_newlines = False
remove_wordbreaks = True # If remove_newlines is False, setting this to true will merge words split across two lines with a - (also removing that line break)
print_summary = True
summary_sentences = 15 # Number of sentences in summary
write_to_text_file = True

#These default parameters have generally worked on all papers tested, but may need to be tweaked a little
mainBodyThreshold = 0.2 # Fraction of text on a page a single font size must comprise to be considered part of the main text
num_heading_sizes = 2 # Top n sizes will be considered headings
cluster_eps = 13 # Increase if random text is missing, decrease if multiple columns are not being separated
column_eps = 175 # Increase if single columns are being split with text in the middle, decrease if multiple columns are not being separated


# Classifies all characters by their font size - other attributes can be used with some modifications
def classifyByStyle(chars):
	styleMap = {}

	for char in chars:
		if char["size"] in styleMap:
			styleMap[char["size"]].append(char)
		else:
			styleMap[char["size"]] = [char]

	return styleMap

def filterByFontSize(chars, acceptableSizes):
	filtered = []

	for char in chars:
		if char["size"] in acceptableSizes:
			filtered.append(char)

	return filtered

# Clusters pages by paragraph, then returns columns of paragraphs - splitting the page into chunks the way a person 
# would read them in English(top to bottom, left to right)
def clusterPage(pageChars, eps=13, columneps = 175):
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
def summarize(text, num_sentences = 7):
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

paper = pdfplumber.open(paperPath)

output = ""

for page in paper.pages:
	pageChars = page.chars

	for char in pageChars:
		char["size"] = round(char["size"], 1)

	smap = classifyByStyle(pageChars)
	mainBodySizes = []
	for size, sizeChars in smap.items():
		if (len(sizeChars)/len(pageChars)) > mainBodyThreshold:
			mainBodySizes.append(size)

	pageChars = filterByFontSize(pageChars, mainBodySizes)

	columns = clusterPage(pageChars, eps = cluster_eps, columneps = column_eps)

	for column in columns:
		output += pdfplumber.utils.extract_text(column, x_tolerance = 1)
		output += "\n"

if remove_wordbreaks:
	output = re.sub('-[\r\n]+', "", output)
if remove_newlines:
	output = output.replace("\n", " ")

if print_result:
	print(output)
if print_summary:
	print('------------------------')
	print('SUMMARY')
	print(summarize(output, summary_sentences))

if write_to_text_file:
	with open(paperPath.replace('.pdf', '.txt'), 'wb') as f:
		f.write(output.encode('utf8'))