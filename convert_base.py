import urllib.parse
from enum import Enum
import re

class RdfRepresent(Enum):
    LINK_REIFIED = 1
    LINK_PRED = 2

class QuoteOptions(Enum):
    CUSTOM = 1
    REMOVE_SPECIAL = 2
    QUOTE_PLUS = 3

def str_to_uri(str, ns, space=None):    
    match space:
        case QuoteOptions.CUSTOM:
            quoted = urllib.parse.quote(str).replace("%20", "_").replace('%3A', ":")
            
        case QuoteOptions.REMOVE_SPECIAL:
            quoted = re.sub("%(\d\d|\d[A-Z])", "", urllib.parse.quote(str))
        
        case _:
            quoted = urllib.parse.quote_plus(str)
        
    return ns[quoted]