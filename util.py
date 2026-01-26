import os, subprocess, re, multiprocess
from rdflib import Namespace, Literal, Graph, BNode, RDF, RDFS, XSD, URIRef
from rdflib.collection import Collection

import time

def run(cmd, printerr=False):    
    start_time = time.perf_counter()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, error = [ b.decode('UTF-8') for b in process.communicate() ]
    end_time = time.perf_counter()
    
    print("time:", (end_time - start_time))
    
    if error.strip() != "" and printerr:
        print("error:", error)

    return out

def rdf_coll(g, *items):
    cnode = BNode()
    coll = Collection(g, cnode, items)
    return cnode