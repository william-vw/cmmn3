import os, subprocess, re, multiprocess
from rdflib import Namespace, Literal, Graph, BNode, RDF, RDFS, XSD, URIRef
from rdflib.collection import Collection
import collections

import time

def run(cmd, get_time=True, printerr=False):
    if get_time:
        start_time = time.perf_counter()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, error = [ b.decode('UTF-8') for b in process.communicate() ]
    if get_time:
        end_time = time.perf_counter()
        print("time:", (end_time - start_time))
    
    if error.strip() != "" and printerr:
        print("error:", error)

    return out

def rdf_coll(g, *items):
    cnode = BNode()
    coll = Collection(g, cnode, items)
    return cnode

def print_coll(coll):
    return "( " + " ".join([ print_rdf(el) for el in coll ]) + " )"

def print_rdf(term):
    if not isinstance(term, str) and isinstance(term, collections.abc.Sequence):
        return print_coll(term)
    else:
        return term.n3()

def print_rdf_stmt(s, p, o):
    return print_rdf(s) + " " + print_rdf(p) + " " + print_rdf(o) + " ."


import urllib.parse

def str_to_uri(str, ns):
    quoted = urllib.parse.quote(str)
    # quoted = quoted.replace("%20", "_").replace('%3A', ":")
    return ns[quoted]

def uri_to_str(uri):    
    return urllib.parse.unquote(uri)

def minmaxnorm(oldmin, oldmax, newmin, newmax, value):
    return newmin + (value - oldmin) / (oldmax - oldmin) * (newmax - newmin)