'''
Set of useful DOM utilities.

@author modified snippets from various people
'''


def remove_ws(node):
    '''
    Recursively removes all of the whitespace-only text decendants of a DOM
    node.
    '''
    condemned = []
    
    # Build up a list of nodes to remove
    for child in node.childNodes:
        if child.nodeType == child.TEXT_NODE and not child.data.strip():
            condemned.append(child)
        
        elif child.hasChildNodes():
            remove_ws(child)
    
    # Then actually remove them
    for node in condemned:
        node.parentNode.removeChild(node)
        node.unlink()
        

def get_root_element(document):
    '''
    Get the root element of a document.
    '''
    for child in document.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            return child
