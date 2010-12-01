'''
Schema Skimmer

Skims out the elements and types you need from an XSD.  You tell the skimmer the
elements you absolutely need and it skims out those elements and the necessary
tree of types.

Facilitates O/XML mapping by reducing an XSD file to only the elements one is
interested in.

@author RGBz
'''

from xml.dom.minidom import parse, parseString
from datetime import datetime
from dom_utils import remove_ws, get_root_element
import sys
import logging

# Set up the logger
logging.basicConfig(level=logging.INFO,
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
        logging.info('Ok, so now I\'m  creating a skimmer')
        
        self.all_xsd_type_elements = []
        self.all_xsd_element_elements = []
        self.targeted_elements = []
        
        logging.info('As part of that I\'m  loading ' + xsd_filename)
        
        try:
            self.doc = parse(xsd_filename)    
        except IOError as e:
            invalid_command('Gah!\nWhat are you trying to do?\nKill me?' \
                     + xsd_filename + ' is either not available or not an XSD.')
                     
        self.schema_element = get_root_element(self.doc)
                     
        logging.info('Booyah, all done loading ' + xsd_filename)

        for element in self.getElementsByTagName(self.doc, 'element'):
            if element.hasAttribute('name'):
                self.all_xsd_element_elements.append(element)

        for complexType in self.getElementsByTagName(self.doc, 'complexType'):
            self.all_xsd_type_elements.append(complexType)

        for simpleType in self.getElementsByTagName(self.doc, 'simpleType'):
            self.all_xsd_type_elements.append(simpleType)

        for group in self.getElementsByTagName(self.doc, 'group'):
            self.all_xsd_type_elements.append(group)
        
        logging.info('Booyah, all done creating a skimmer')
        
    def getElementsByTagName(self, root, tag_name):
        '''
        Simplifies getElementsByTagName calls by removing the need to know
        namespaces or prefixes.
        '''
        return root.getElementsByTagNameNS(self.schema_element.namespaceURI,
                                           tag_name)

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
        if type not in self.targeted_elements:

            logging.debug('Adding ' + type.localName + ' ' + type_name)
            self.targeted_elements.append(type)

            # If the element is complex, add its children
            if type.localName in ['complexType', 'group']:
                
                # Handle elements
                for element in self.getElementsByTagName(type, 'element'):
                    self.addElement(element)
                    if element.hasAttribute('ref'):
                        self.addElementByName(element.getAttribute('ref'))
                    elif element.hasAttribute('name'):
                        self.addElementByName(element.getAttribute('name'))
                
                # Handle groups
                for group in self.getElementsByTagName(type, 'group'):
                    self.addElement(group)
                    if group.hasAttribute('ref'):
                        self.addTypeByName(group.getAttribute('ref'))
                    elif element.hasAttribute('name'):
                        self.addTypeByName(element.getAttribute('type'))
                        
                # Handle attributes
                for attribute in self.getElementsByTagName(type, 'attribute'):
                    self.addTypeByName(attribute.getAttribute('type'))
                    
                # Handle super class extension
                if len(self.getElementsByTagName(type, 'complexContent')) > 0:
                    alter_elems = self.getElementsByTagName(type, 'extension')
                    if len(alter_elems) == 0:
                        alter_elems = self.getElementsByTagName(type,
                                                                'restriction')
                    self.addTypeByName(alter_elems[0].getAttribute('base'))
                    
    def addElement(self, element):
        if element not in self.targeted_elements:
            logging.debug('Adding element \''+ str(element) + '\'')
            self.targeted_elements.append(element)

    def addElementByName(self, element_name):
        '''
        Add an element and its type to our lists.
        '''
        for element in self.all_xsd_element_elements:
            if element.getAttribute('name') == element_name:
                if element not in self.targeted_elements:
                    logging.debug('Adding element \''+ element_name + '\'')
                    self.targeted_elements.append(element)
                    self.addTypeByName(element.getAttribute('type'))

    def reduce(self):
        '''
        Remove all non-targeted elements and types.
        '''
        logging.info('Ok, so now I\'m removing uneeded nodes')
        
        dif = set(self.all_xsd_element_elements).union(
                self.all_xsd_type_elements).difference(
                        set(self.targeted_elements))

        for elem in dif:
            logging.debug('Removing ' + elem.localName + ' '
                    + elem.getAttribute('name'))
            elem.parentNode.removeChild(elem)
            
        logging.info('Booyah, all done removing uneeded nodes')

    def writeToXml(self, filename):
        '''
        Write the reduced XML to a file.
        '''
        self.reduce()
        
        logging.info('Ok, so now I\'m  removing whitespace nodes '
                     + '(I\'d go for a walk this usually takes a while)')
        
        remove_ws(self.doc)
        
        logging.info('Booyah, all done removing whitespace nodes')

        logging.info('Ok, so now I\'m  writing new XSD to ' + filename)
        
        with open(filename, 'w') as f:
            try:
                f.write(self.doc.toprettyxml(indent='  ').encode('utf-8'))
            except AttributeError as e:
                logging.error('Shoot!  It looks like your XSD contains an '
                              + 'element that triggered a weird bug in '
                              + 'Python\'s minidom.py code.  This bug is '
                              + 'currently resolved but hasn\'t yet made it '
                              + 'into a release.  In the short term, you can '
                              + 'copy the included '
                              + 'in_case_of_emergency/minidom.py over your '
                              + 'minidom.py in your Python library folder to '
                              + 'fix the issue.\n\n'
                              + 'For reference, you can see the bug and '
                              + 'its details here: '
                              + 'http://bugs.python.org/issue5762')
                exit()

        logging.info('Booyah, all done writing new XSD to ' + filename)


def invalid_command(message):
    '''
    Print how to do the commands correctly.
    '''
    print(message)
    print('')
    print('Relax, take a breath and this time do it like this:')
    print('$> python schema_skimmer.py [XSD_FILENAME] [ELEMENT_NAME_1] ...')
    print('')
    print('Or like this (if you have a newline delimited file listing element '
          + 'names):')
    print('$> python schema_skimmer.py -f [XSD_FILENAME] '
          + '[ELEMENT_LIST_FILENAME]')
    print('')
    exit()


def main(args):
    '''
    Main method, runs the program.
    '''
    # Make sure we have more than two command line arguments
    if len(args) <= 2:
        invalid_command('Nope!\nYou\'re doing it wrong.')
    
    start = datetime.now()

    logging.info('Looks like I\'m starting at ' + str(start))

    xsd_filename = None
    element_names = []

    # If this is file based, load up the file
    if args[1] == '-f':
        logging.debug('Reading in elements from' + args[1])
        xsd_filename = args[2]
        if not len(args) == 4:
            invalid_command('Aah!\nWhat\'re you doing?\n'
                            + 'You need to specify a filename for the list '
                            + 'of elements if you use the -f mode.')
        with open(args[3], 'r') as f:
            element_names = f.read().split()
        
        logging.info('Just loaded up ' + args[3])
                    
    # Otherwise use the element names from the command line
    else:
        xsd_filename = args[1]
        for element_name in args[2:]:
            logging.debug('Adding in requirement for ' + element_name)
            element_names.append(element_name)

    # Load up the XSD
    skimmer = SchemaSkimmer(xsd_filename)
    
    logging.info('Ok, so now I\'m skimming out the elements you asked for and '
                 + 'the types they require')
    
    # Skim on each element you want
    for name in element_names:
        skimmer.addElementByName(name)

    # Write out the file with a new extension
    skimmed_xsd_filename = xsd_filename[:xsd_filename.rindex('.')] \
                           + '-skimmed.xsd'
    skimmer.writeToXml(skimmed_xsd_filename)
    
    finish = datetime.now()
    logging.info('Booyah, all done at ' + str(finish))
    logging.info('It only took me ' + str(finish - start))


# Run the main method
main(sys.argv)

