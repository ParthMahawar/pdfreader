PDFReader - Obtain main-body text from PDFs with support for multi-column layouts.

DESCRIPTION
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

CLASSES
    builtins.object
        PDFReader
    
    class PDFReader(builtins.object)
     |  PDFReader(PDFPath: str, remove_newlines: bool = False, remove_wordbreaks: bool = True, summary_sentences: int = 15)
     |  
     |  Each instance of this class will handle one PDF with its own settings.
     |  
     |  Attributes:
     |          PDFPath (str): File path of PDF to be parsed
     |          remove_newlines (bool): If true, all newline characters from
     |                  the parsed text will be removed, to get the text in one continuous
     |                  block. Defaults to False.
     |          remove_wordbreaks (bool): If true, will remove newlines when the previous line
     |                  ends on a '-' character, removing cases where a word is split across
     |                  two lines. Defaults to True.
     |          summary_sentences (int): Default number of sentences in output summary. (Experimental)
     |          mainBodyThreshold (float): Defines what fraction of the text on a page
     |                  a certain font size must comprise to be considered part of the output
     |                  main body text. Defaults to 0.2 (i.e. 20% of text on the page).
     |          cluster_eps (float): Determines how much of a gap between text is tolerated
     |                  while keeping the text in the same cluster. Increase this number if
     |                  random text on the page is missing or out of place, and decrease it if
     |                  text on multiple columns is not separated. Defaults to 13.
     |          column_eps (float): Determines how much of gap between text clusters is tolerated
     |                  while keeping them in the same column of text. Increase this number if single
     |                  columns are showing up with text out of order, or decrease them if columns
     |                  are not separated. Defaults to 175.
     |  
     |  Note:
     |          The default values for the cluster_eps and column_eps attributes have been selected
     |          based on PDFs formatted as Letter/A4 sized paper. If the PDF is formatted as 
     |          a different size of paper, it's likely that these attributes will have to be
     |          scaled accordingly.
     |  
     |  Methods defined here:
     |  
     |  __init__(self, PDFPath: str, remove_newlines: bool = False, remove_wordbreaks: bool = True, summary_sentences: int = 15)
     |      Initializes PDF Reader object for given PDF.
     |      
     |      See PDFReader class docstring for more info on these attributes
     |      Args:
     |              PDFPath (str): Sets PDFPath attribute.
     |              remove_newlines (bool, optional): Sets remove_newlines attribute.
     |              remove_wordbreaks (bool, optional): Sets remove_wordbreaks attribute.
     |              summary_sentences (int, optional): Sets summary_sentences attribute.
     |  
     |  classifyByStyle(self, chars: list) -> dict[float, list]
     |      Classifies pdfplumber characters based on their font size.
     |      
     |      Args:
     |              chars (list): A list of pdfplumber characters.
     |      
     |      Returns:
     |              dict[float, list]: A dictionary with keys for each font size, with
     |                      the respective values being a list of the input characters that
     |                      had the corresponding font size as their 'size' property.
     |  
     |  clusterPage(self, pageChars: list, eps: int = None, columneps: int = None) -> list[list]
     |      Returns columns of pdfplumber chars from input list.
     |      
     |      Using the DBSCAN method, this function uses the characters' x and y
     |      positions to cluster them, then uses the centroids of those clusters
     |      to classify them by which text column they belong to.
     |      
     |      Args:
     |              pageChars (list): A list of pdfplumber characters.
     |              eps (float, optional): Cluster epsilon. See cluster_eps attribute 
     |                      in PDFReader class docstring for more details.
     |              columneps (float, optional): Column Epsilon. See column_eps
     |                      attribute in PDFReader class docstring for more details.
     |      
     |      Returns:
     |              list[list]: A list of columns in the page, left to right. Each
     |                      column is represented as a list of pdfplumber characters.
     |  
     |  filterByFontSize(self, chars: list, acceptableSizes: list[float]) -> list
     |      Filters list of pdfplumber characters, keeping only certain font sizes.
     |      
     |      Args:
     |              chars (list): A list of pdfplumber characters.
     |              acceptableSizes (list[float]): A list of font sizes to keep.
     |      
     |      Returns:
     |              list: List of pdfplumber characters that had an acceptable
     |                      'size' value.
     |  
     |  get_raw_chars(self) -> list
     |      Obtain all the the pdfplumber char objects from the PDF.
     |      
     |      Returns:
     |              list: A list of all the pdfplumber char objects from the PDF as is.
     |  
     |  get_text(self) -> str
     |      Gets full main body text from PDF.
     |      
     |      Returns:
     |              str: Main Body of PDF, settings based on instance attributes.
     |  
     |  summarize(self, num_sentences: int = None) -> str
     |      Summarizes the pdf text using a rather simple algorithm.
     |      
     |      This is a very basic summarizer that may or may not give great results,
     |      relying on scoring words by how often they occur in the text, and then
     |      ranking sentences based on the total scores of the words in them, returning
     |      the highest ranking sentences in order of their appearance in the text.
     |      Works better for text that is a continuous block of text sentences without
     |      interruption by mathematical notation etc.
     |      
     |      Args:
     |              num_sentences(int, optional): Number of sentences in summary. Defaults
     |                      to num_sentences attribute of instance.
     |      
     |      Returns:
     |              str: Summary of input text
     |  
     |  write_to_text_file(self, textFilePath: str)
     |      Write text from PDF to a file.
     |      
     |      Args:
     |              textFilePath (str): Path of file to be written.
     |  
     |  ----------------------------------------------------------------------
     |  Data descriptors defined here:
     |  
     |  __dict__
     |      dictionary for instance variables
     |  
     |  __weakref__
     |      list of weak references to the object


