'''
Schema Skimmer

Skims out the elements and types you need from an XSD.  You tell the skimmer the
elements you absolutely need and it skims out those elements and the necessary
tree of types.

Facilitates O/XML mapping by reducing an XSD file to only the elements one is
interested in.

@author RGBz
'''

from minidom_with_bug_fix import parse, parseString
from datetime import datetime
from dom_utils import remove_ws
import sys
import logging

# Set up the logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    filename='skimmer.log',
                    filemode='w')

# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)

# set a format which is simpler for console use
formatter = logging.Formatter('%(message)s')

# tell the handler to use this format
console.setFormatter(formatter)

# add the handler to the root logger
logging.getLogger('').addHandler(console)


class SchemaSkimmer(object):
    '''
    Skims out the requested elements and types from an XSD document.
    '''

    def __init__(self, xsd_filename):
        '''
        Constructor that loads up an XSD and initializes some lists on XSD data.
        '''
        logging.info('Started creating skimmer')
        
        self.all_xsd_type_elements = []
        self.targeted_xsd_type_elements = []
        
        self.all_xsd_element_elements = []
        self.targeted_xsd_element_elements = []

        logging.info('Started loading ' + xsd_filename)
        self.doc = parse(xsd_filename)
        logging.info('Finished loading ' + xsd_filename)        

        for element in self.getElementsByTagName(self.doc, 'element'):
            if element.hasAttribute('name'):
                self.all_xsd_element_elements.append(element)

        for complexType in self.getElementsByTagName(self.doc, 'complexType'):
            self.all_xsd_type_elements.append(complexType)

        for simpleType in self.getElementsByTagName(self.doc, 'simpleType'):
            self.all_xsd_type_elements.append(simpleType)

        for group in self.getElementsByTagName(self.doc, 'group'):
            self.all_xsd_type_elements.append(group)
        
        logging.info('Finished creating skimmer')
        
    def getElementsByTagName(self, root, tag_name):
        '''
        Simplifies getElementsByTagName calls by removing the need to know
        namespaces or prefixes.
        '''
        return root.getElementsByTagNameNS(self.doc.namespaceURI, tag_name)

    def getTypeByName(self, type_name):
        '''
        Get a type from the list of all types by its name.
        '''
        # Rip out that damn prefix
        if ':' in type_name:
            type_name = type_name.split(':')[1]
        
        # Find the type we want
        for type in self.all_xsd_type_elements:
            if type.getAttribute('name') == type_name:
                return type

    def addTypeByName(self, type_name):
        '''
        Add a type by name from the list of all types to the list of targeted
        types if it's not on the list of targeted types already.
        '''
        # Only add types with names
        if type_name.strip() == '':
            return

        # Get our type by its name
        type = self.getTypeByName(type_name)

        # If we don't already have it in our list, add it
        if type not in self.targeted_xsd_type_elements:

            logging.info('Adding ' + type.localName + ' ' + type_name)
            self.targeted_xsd_type_elements.append(type)

            # If the element is complex, add its children
            if type.localName in ['complexType', 'group']:
                
                # Handle elements
                for element in self.getElementsByTagName(type, 'element'):
                    if element.hasAttribute('ref'):
                        self.addElementByName(element.getAttribute('ref'))
                    elif element.hasAttribute('name'):
                        self.addElementByName(element.getAttribute('name'))
                
                # Handle groups
                for group in getElementsByTagName(type, 'group'):
                    if group.hasAttribute('ref'):
                        self.addTypeByName(group.getAttribute('ref'))
                    elif element.hasAttribute('name'):
                        self.addTypeByName(element.getAttribute('type'))
                        
                # Handle attributes
                for attribute in getElementsByTagName(type, 'attribute'):
                    self.addTypeByName(attribute.getAttribute('type'))
                    
                # Handle super class extension
                if len(getElementsByTagName(type, 'complexContent')) > 0:
                    alter_elems = getElementsByTagName(type, 'extension')
                    if len(alter_elems) == 0:
                        alter_elems = getElementsByTagName(type, 'restriction')
                    self.addTypeByName(alter_elems[0].getAttribute('base'))

    def addElementByName(self, element_name):
        '''
        Add an element and its type to our lists.
        '''
        for element in self.all_xsd_element_elements:
            if element.getAttribute('name') == element_name:
                if element not in self.targeted_xsd_element_elements:
                    logging.info('Adding element \''+ element_name + '\'')
                    self.targeted_xsd_element_elements.append(element)
                    self.addTargetedType(element.getAttribute('type'))

    def filterByElementNames(self, element_names):
        '''
        Add types to the targeted types list starting with the root
        elements.
        '''
        logging.info('Started skimming by element names ' + str(element_names))
        
        for element_name in element_names:
            self.addElementByName(element_name)

        logging.info('Finished skimming by element names ' + str(element_names))
            
    def reduce(self):
        '''
        Remove all non-targeted elements and types.
        '''
        logging.info('Started removing uneeded nodes')
        
        dif = set(self.all_xsd_element_elements).difference(
                set(self.targeted_xsd_element_elements))
        
        for elem in dif:
            logging.info('Removing ' + elem.localName + ' '
                    + elem.getAttribute('name'))
            elem.parentNode.removeChild(elem)
        
        dif = set(self.all_xsd_type_elements).difference(
                set(self.targeted_xsd_type_elements))
        
        for elem in dif:
            logging.info('Removing ' + elem.localName + ' '
                    + elem.getAttribute('name'))
            elem.parentNode.removeChild(elem)
            
        logging.info('Finished removing uneeded nodes')

    def writeToXml(self, filename):
        '''
        Write the reduced XML to a file.
        '''
        self.reduce()
        
        # Log the element details
        for type in skimmer.targeted_xsd_type_elements:
            if type.localName == 'simpleType':
                logging.info(type.localName + ' ' + type.getAttribute('name'))
                
                for elem in type.childNodes:
                    if elem.nodeType == elem.ELEMENT_NODE \
                       and elem.hasAttribute('base'):
                        logging.info(elem.getAttribute('base'))

            else:
                if len(skimmer.getElementsByTagName(type, 'simpleContent')) > 0:
                    logging.info(type.localName + ' '
                                  + type.getAttribute('name') + ' ')
                    
                    for elem in skimmer.getElementsByTagName(type,
                            'simpleContent')[0].childNodes:
                        if elem.nodeType == elem.ELEMENT_NODE \
                           and elem.hasAttribute('base'):
                            logging.info(elem.getAttribute('base'))
                else:
                    logging.info(type.localName + ' '
                                  + type.getAttribute('name') + '\n')
    
        for element in skimmer.targeted_xsd_element_elements:
            logging.info(element.localName + ' '

                          + element.getAttribute('name')
                          + ' type ' + element.getAttribute('type'))
        
        logging.info('Started removing whitespace nodes')
        
        remove_ws(self.doc)
        
        logging.info('Finished removing whitespace nodes')

        logging.info('Started writing new XSD to ' + filename)
        
        with open(filename, 'w') as f:
            f.write(self.doc.toprettyxml(indent='    ').encode('utf-8'))

        logging.info('Finished writing new XSD to ' + filename)


def invalid_command():
    '''
    Print how to do the commands correctly.
    '''
    print('Nope.')
    print('You\'re doing it wrong.')
    print('Instead, do it like this:')
    print('$> python schema_skimmer.py [XSD_FILENAME] [ELEMENT_NAME_1] ...')
    print('Or like this (if you have a newline delimited file listing element '
          + 'names):')
    print('$> python schema_skimmer.py -f [XSD_FILENAME] '
          + '[ELEMENT_LIST_FILENAME]')


# Make sure we have more than two command line arguments
if len(sys.argv) > 2:
    start = datetime.now()
    
    logging.info('Started at ' + str(start))
    
    # Load up the XSD
    skimmer = SchemaSkimmer(sys.argv[1])
    
    # If this is file based, load up the file
    if sys.argv[2] == '-f':
        if len(sys.argv) > 3:
            invalid_command()
        
        else:
            with open(sys.argv[3], 'r') as f:
                for line in f:
                    skimmer.addElementByName(line.strip())
    
    # Otherwise use the element names from the command line
    else:
        for element_name in sys.argv[2:]:
            skimmer.addElementByName(element_name)
    
    # Write out the file with a new extension
    skimmer.writeToXml(sys.argv[1].replace('.xsd', '-reduced.xsd'))
    
    finish = datetime.now()
    
    logging.info('Finished at ' + str(finish))
    logging.info('Duration ' + str(finish - start))
    
else:
    invalid_command()
