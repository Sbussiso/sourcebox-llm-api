# This app combines Generative AI with common file readers to perform RAG with local files and folders



## Current Models

- OpenAI GPT-4o

## Performs RAG with

- Files
- Folders


## Requirements

- internet connection for AI model
- File/Folder Paths to perform RAG



## Supported Files:

- Text files (.txt, .py, etc.) – handled by read_plain_text().
- PDF files (.pdf) – handled by read_pdf() via PyPDF2.
- Word documents (.docx) – handled by read_word_doc() via python-docx.
- Excel files (.xlsx) – handled by read_excel() via openpyxl.
- CSV files (.csv) – handled by read_csv() via the csv module.
- JSON files (.json) – handled by read_json() via the json module.
- HTML files (.html) – handled by read_html() via BeautifulSoup.
- XML files (.xml) – handled by read_xml() via xml.etree.ElementTree.
- YAML files (.yaml, .yml) – handled by read_yaml() via PyYAML.
- INI configuration files (.ini) – handled by read_ini() via configparser.
