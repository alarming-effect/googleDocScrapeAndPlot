import googleapiclient.discovery as discovery
from httplib2 import Http
from oauth2client import client
from oauth2client import file
from oauth2client import tools

SCOPES = 'https://www.googleapis.com/auth/documents.readonly'
DISCOVERY_DOC = 'https://docs.googleapis.com/$discovery/rest?version=v1'
DOCUMENT_ID = 'YOUR_DOCUMENT_ID'


def get_credentials():
  """Gets valid user credentials from storage.

  If nothing has been stored, or if the stored credentials are invalid,
  the OAuth 2.0 flow is completed to obtain the new credentials.

  Returns:
      Credentials, the obtained credential.
  """
  store = file.Storage('token.json')
  credentials = store.get()

  if not credentials or credentials.invalid:
    flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
    credentials = tools.run_flow(flow, store)
  return credentials


def add_current_and_child_tabs(tab, all_tabs):
  """Adds the provided tab to the list of all tabs, and recurses through and
  adds all child tabs.

  Args:
      tab: a Tab from a Google Doc.
      all_tabs: a list of all tabs in the document.
  """
  all_tabs.append(tab)
  for tab in tab.get('childTabs'):
    add_current_and_child_tabs(tab, all_tabs)


def get_all_tabs(doc):
  """Returns a flat list of all tabs in the document in the order they would
  appear in the UI (top-down ordering). Includes all child tabs.

  Args:
      doc: a document.
  """
  all_tabs = []
  # Iterate over all tabs and recursively add any child tabs to generate a
  # flat list of Tabs.
  for tab in doc.get('tabs'):
    add_current_and_child_tabs(tab, all_tabs)
  return all_tabs


def read_paragraph_element(element):
  """Returns the text in the given ParagraphElement.

  Args:
      element: a ParagraphElement from a Google Doc.
  """
  text_run = element.get('textRun')
  if not text_run:
    return ''
  return text_run.get('content')


def read_structural_elements(elements):
  """Recurses through a list of Structural Elements to read a document's text
  where text may be in nested elements.

  Args:
      elements: a list of Structural Elements.
  """
  text = ''
  for value in elements:
    if 'paragraph' in value:
      elements = value.get('paragraph').get('elements')
      for elem in elements:
        text += read_paragraph_element(elem)
    elif 'table' in value:
      # The text in table cells are in nested Structural Elements and tables may
      # be nested.
      table = value.get('table')
      for row in table.get('tableRows'):
        cells = row.get('tableCells')
        for cell in cells:
          text += read_structural_elements(cell.get('content'))
    elif 'tableOfContents' in value:
      # The text in the TOC is also in a Structural Element.
      toc = value.get('tableOfContents')
      text += read_structural_elements(toc.get('content'))
  return text


def main():
  """Uses the Docs API to print out the text of a document."""
  credentials = get_credentials()
  http = credentials.authorize(Http())
  docs_service = discovery.build(
      'docs', 'v1', http=http, discoveryServiceUrl=DISCOVERY_DOC
  )
  # Fetch the document with all of the tabs populated, including any nested
  # child tabs.
  doc = (
      docs_service.documents()
      .get(documentId=DOCUMENT_ID, include_tabs_content=True)
      .execute()
  )
  all_tabs = get_all_tabs(doc)

  # Print the text from each tab in the document.
  for tab in all_tabs:
    # Get the DocumentTab from the generic Tab.
    document_tab = tab.get('documentTab')
    doc_content = document_tab.get('body').get('content')
    print(read_structural_elements(doc_content))


if __name__ == '__main__':
  main()
