import os
from typing import List

import pytest

from kgx.transformer import Transformer
from tests import RESOURCE_DIR, TARGET_DIR
from tests.integration import (
    DEFAULT_NEO4J_URL,
    DEFAULT_NEO4J_USERNAME,
    DEFAULT_NEO4J_PASSWORD,
)


def _transform(query):
    """
    Transform an input to an output via Transformer.
    """
    t1 = Transformer()
    t1.transform(query[0])
    t1.save(query[1].copy())

    assert t1.store.graph.number_of_nodes() == query[2]
    assert t1.store.graph.number_of_edges() == query[3]

    output = query[1]
    if output['format'] in {'tsv', 'csv', 'jsonl'}:
        input_args = {
            'filename': [
                f"{output['filename']}_nodes.{output['format']}",
                f"{output['filename']}_edges.{output['format']}",
            ],
            'format': output['format'],
        }
    elif output['format'] in {'neo4j'}:
        input_args = {
            'uri': DEFAULT_NEO4J_URL,
            'username': DEFAULT_NEO4J_USERNAME,
            'password': DEFAULT_NEO4J_PASSWORD,
            'format': 'neo4j',
        }
    else:
        input_args = {'filename': [f"{output['filename']}"], 'format': output['format']}

    t2 = Transformer()
    t2.transform(input_args)

    assert t2.store.graph.number_of_nodes() == query[2]
    assert t2.store.graph.number_of_edges() == query[3]


@pytest.mark.parametrize(
    'query',
    [
        ({'category': {'biolink:Gene', 'biolink:Disease'}}, {}, 2, 1),
        (
            {'category': {'biolink:Gene', 'biolink:Disease', 'biolink:PhenotypicFeature'}},
            {'validated': 'true'},
            3,
            2,
        ),
        (
            {'category': {'biolink:Gene', 'biolink:PhenotypicFeature'}},
            {
                'subject_category': {'biolink:Gene'},
                'object_category': {'biolink:PhenotypicFeature'},
                'predicate': {'biolink:related_to'},
            },
            2,
            1,
        ),
    ],
)
def test_transform_filters1(query):
    """
    Test transform with filters.
    """
    input_args = {
        'filename': [
            os.path.join(RESOURCE_DIR, 'test2_nodes.tsv'),
            os.path.join(RESOURCE_DIR, 'test2_edges.tsv'),
        ],
        'format': 'tsv',
        'node_filters': query[0],
        'edge_filters': query[1],
    }
    t = Transformer()
    t.transform(input_args)
    assert t.store.graph.number_of_nodes() == query[2]
    assert t.store.graph.number_of_edges() == query[3]


@pytest.mark.parametrize(
    'query',
    [
        ({}, {}, 512, 532),
        ({'category': {'biolink:Gene'}}, {}, 178, 178),
        (
            {'category': {'biolink:Gene'}},
            {'subject_category': {'biolink:Gene'}, 'object_category': {'biolink:Gene'}},
            178,
            178,
        ),
        (
            {'category': {'biolink:Gene'}},
            {
                'subject_category': {'biolink:Gene'},
                'object_category': {'biolink:Gene'},
                'predicate': {'biolink:orthologous_to'},
            },
            178,
            13,
        ),
        ({'category': {'biolink:Gene'}}, {'predicate': {'biolink:interacts_with'}}, 178, 165),
        ({}, {'provided_by': {'omim', 'hpoa', 'orphanet'}}, 512, 166),
        ({}, {'subject_category': {'biolink:Disease'}}, 56, 35),
        ({}, {'object_category': {'biolink:Disease'}}, 22, 20),
    ],
)
def test_transform_filters2(query):
    """
    Test transform with filters.
    """
    input_args = {
        'filename': [
            os.path.join(RESOURCE_DIR, 'graph_nodes.tsv'),
            os.path.join(RESOURCE_DIR, 'graph_edges.tsv'),
        ],
        'format': 'tsv',
        'node_filters': query[0],
        'edge_filters': query[1],
        'lineterminator': None,
    }
    t = Transformer()
    t.transform(input_args)

    assert t.store.graph.number_of_nodes() == query[2]
    assert t.store.graph.number_of_edges() == query[3]


@pytest.mark.parametrize(
    "query",
    [
        ({'category': {'biolink:Gene'}}, {}, 2, 0),
        ({'category': {'biolink:Protein'}}, {}, 4, 3),
        ({'category': {'biolink:Protein'}}, {'predicate': {'biolink:interacts_with'}}, 4, 1),
    ],
)
def test_rdf_transform_with_filters1(query):
    """
    Test RDF transform with filters.
    """
    input_args = {
        'filename': [os.path.join(RESOURCE_DIR, 'rdf', 'test3.nt')],
        'format': 'nt',
        'node_filters': query[0],
        'edge_filters': query[1],
    }
    t = Transformer()
    t.transform(input_args)

    assert t.store.graph.number_of_nodes() == query[2]
    assert t.store.graph.number_of_edges() == query[3]


def test_rdf_transform1():
    """
    Test parsing an RDF N-triple, with user defined prefix map,
    and node property predicates.
    """
    prefix_map = {
        'HGNC': 'https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/',
        'OMIM': 'http://omim.org/entry/',
    }

    node_property_predicates = {
        'http://purl.obolibrary.org/obo/RO_0002558',
        'http://purl.org/dc/elements/1.1/source',
        'https://monarchinitiative.org/frequencyOfPhenotype',
    }
    input_args1 = {
        'filename': [os.path.join(RESOURCE_DIR, 'rdf', 'oban-test.nt')],
        'format': 'nt',
        'prefix_map': prefix_map,
        'node_property_predicates': node_property_predicates,
    }
    t1 = Transformer()
    t1.transform(input_args1)
    assert t1.store.graph.number_of_nodes() == 14
    assert t1.store.graph.number_of_edges() == 7

    n1 = t1.store.graph.nodes()['HP:0000505']
    assert len(n1['category']) == 1
    assert 'biolink:NamedThing' in n1['category']

    e1 = list(t1.store.graph.get_edge('OMIM:166400', 'HP:0000006').values())[0]
    assert e1['subject'] == 'OMIM:166400'
    assert e1['object'] == 'HP:0000006'
    assert e1['relation'] == 'RO:0000091'
    assert e1['type'] == 'OBAN:association'
    assert e1['has_evidence'] == 'ECO:0000501'

    e2 = list(t1.store.graph.get_edge('ORPHA:93262', 'HP:0000505').values())[0]
    assert e2['subject'] == 'ORPHA:93262'
    assert e2['object'] == 'HP:0000505'
    assert e2['relation'] == 'RO:0002200'
    assert e2['type'] == 'OBAN:association'
    assert e2['frequencyOfPhenotype'] == 'HP:0040283'

    output_args = {'filename': os.path.join(TARGET_DIR, 'oban-export.nt'), 'format': 'nt'}
    t1.save(output_args)

    input_args2 = {
        'filename': [os.path.join(TARGET_DIR, 'oban-export.nt')],
        'format': 'nt',
        'prefix_map': prefix_map,
    }
    t2 = Transformer()
    t2.transform(input_args2)

    assert t2.store.graph.number_of_nodes() == 14
    assert t2.store.graph.number_of_edges() == 7


def test_rdf_transform2():
    """
    Test parsing an RDF N-triple, with user defined prefix map,
    node property predicates, and predicate mappings.
    """
    prefix_map = {
        'HGNC': 'https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/',
        'OMIM': 'http://omim.org/entry/',
    }
    node_property_predicates = {
        'http://purl.obolibrary.org/obo/RO_0002558',
        'http://purl.org/dc/elements/1.1/source',
        'https://monarchinitiative.org/frequencyOfPhenotype',
    }
    predicate_mappings = {
        'http://purl.org/dc/elements/1.1/source': 'source',
        'https://monarchinitiative.org/frequencyOfPhenotype': 'frequency_of_phenotype',
    }
    input_args1 = {
        'filename': [os.path.join(RESOURCE_DIR, 'rdf', 'oban-test.nt')],
        'format': 'nt',
        'prefix_map': prefix_map,
        'node_property_predicates': node_property_predicates,
        'predicate_mappings': predicate_mappings,
    }
    t1 = Transformer()
    t1.transform(input_args1)

    assert t1.store.graph.number_of_nodes() == 14
    assert t1.store.graph.number_of_edges() == 7

    n1t1 = t1.store.graph.nodes()['HP:0000505']
    assert len(n1t1['category']) == 1
    assert 'biolink:NamedThing' in n1t1['category']

    e1t1 = list(t1.store.graph.get_edge('OMIM:166400', 'HP:0000006').values())[0]
    assert e1t1['subject'] == 'OMIM:166400'
    assert e1t1['object'] == 'HP:0000006'
    assert e1t1['relation'] == 'RO:0000091'
    assert e1t1['type'] == 'OBAN:association'
    assert e1t1['has_evidence'] == 'ECO:0000501'
    assert e1t1['source'] == 'OMIM:166400'

    e2t1 = list(t1.store.graph.get_edge('ORPHA:93262', 'HP:0000505').values())[0]
    assert e2t1['subject'] == 'ORPHA:93262'
    assert e2t1['object'] == 'HP:0000505'
    assert e2t1['relation'] == 'RO:0002200'
    assert e2t1['type'] == 'OBAN:association'
    assert e2t1['frequency_of_phenotype'] == 'HP:0040283'
    assert e2t1['source'] == 'ORPHA:93262'

    property_types = {'frequency_of_phenotype': 'uriorcurie', 'source': 'uriorcurie'}
    output_args1 = {
        'filename': os.path.join(TARGET_DIR, 'oban-export.nt'),
        'format': 'nt',
        'property_types': property_types,
    }
    t1.save(output_args1)

    input_args2 = {'filename': [os.path.join(TARGET_DIR, 'oban-export.nt')], 'format': 'nt'}
    t2 = Transformer()
    t2.transform(input_args2)
    assert t2.store.graph.number_of_nodes() == 14
    assert t2.store.graph.number_of_edges() == 7

    n1t2 = t2.store.graph.nodes()['HP:0000505']
    assert len(n1t2['category']) == 1
    assert 'biolink:NamedThing' in n1t2['category']

    e1t2 = list(t2.store.graph.get_edge('OMIM:166400', 'HP:0000006').values())[0]
    assert e1t2['subject'] == 'OMIM:166400'
    assert e1t2['object'] == 'HP:0000006'
    assert e1t2['relation'] == 'RO:0000091'
    assert e1t2['type'] == 'biolink:Association'
    assert e1t2['has_evidence'] == 'ECO:0000501'
    assert e1t2['source'] == 'OMIM:166400'

    e2t2 = list(t2.store.graph.get_edge('ORPHA:93262', 'HP:0000505').values())[0]
    assert e2t2['subject'] == 'ORPHA:93262'
    assert e2t2['object'] == 'HP:0000505'
    assert e2t2['relation'] == 'RO:0002200'
    assert e2t2['type'] == 'biolink:Association'
    assert e2t2['frequency_of_phenotype'] == 'HP:0040283'
    assert e2t2['source'] == 'ORPHA:93262'

    input_args3 = {'filename': [os.path.join(TARGET_DIR, 'oban-export.nt')], 'format': 'nt'}
    t3 = Transformer()
    t3.transform(input_args3)
    assert t3.store.graph.number_of_nodes() == 14
    assert t3.store.graph.number_of_edges() == 7

    n1t3 = t1.store.graph.nodes()['HP:0000505']
    assert len(n1t3['category']) == 1
    assert 'biolink:NamedThing' in n1t3['category']

    e1t3 = list(t3.store.graph.get_edge('OMIM:166400', 'HP:0000006').values())[0]
    assert e1t3['subject'] == 'OMIM:166400'
    assert e1t3['object'] == 'HP:0000006'
    assert e1t3['relation'] == 'RO:0000091'
    assert e1t3['type'] == 'biolink:Association'
    assert e1t3['has_evidence'] == 'ECO:0000501'
    assert e1t3['source'] == 'OMIM:166400'

    e2t3 = list(t3.store.graph.get_edge('ORPHA:93262', 'HP:0000505').values())[0]
    assert e2t3['subject'] == 'ORPHA:93262'
    assert e2t3['object'] == 'HP:0000505'
    assert e2t3['relation'] == 'RO:0002200'
    assert e2t3['type'] == 'biolink:Association'
    assert e2t3['frequency_of_phenotype'] == 'HP:0040283'
    assert e2t3['source'] == 'ORPHA:93262'


def test_rdf_transform3():
    """
    Test parsing an RDF N-triple and round-trip.
    """
    input_args1 = {'filename': [os.path.join(RESOURCE_DIR, 'rdf', 'test1.nt')], 'format': 'nt'}
    t1 = Transformer()
    t1.transform(input_args1)
    assert t1.store.graph.number_of_nodes() == 2
    assert t1.store.graph.number_of_edges() == 1

    output_args1 = {'filename': os.path.join(TARGET_DIR, 'test1-export.nt'), 'format': 'nt'}
    t1.save(output_args1)

    input_args2 = {'filename': [os.path.join(TARGET_DIR, 'test1-export.nt')], 'format': 'nt'}
    t2 = Transformer()
    t2.transform(input_args2)
    assert t2.store.graph.number_of_nodes() == 2
    assert t2.store.graph.number_of_edges() == 1

    n1t1 = t1.store.graph.nodes()['ENSEMBL:ENSG0000000000001']
    n1t2 = t2.store.graph.nodes()['ENSEMBL:ENSG0000000000001']
    n1t3 = t2.store.graph.nodes()['ENSEMBL:ENSG0000000000001']

    assert n1t1['type'] == n1t2['type'] == n1t3['type'] == 'SO:0000704'
    assert len(n1t1['category']) == len(n1t2['category']) == len(n1t3['category']) == 4
    assert (
        'biolink:Gene' in n1t1['category']
        and 'biolink:Gene' in n1t2['category']
        and 'biolink:Gene' in n1t3['category']
    )
    assert (
        'biolink:GenomicEntity' in n1t1['category']
        and 'biolink:GenomicEntity' in n1t2['category']
        and 'biolink:GenomicEntity' in n1t3['category']
    )
    assert (
        'biolink:NamedThing' in n1t1['category']
        and 'biolink:NamedThing' in n1t2['category']
        and 'biolink:NamedThing' in n1t3['category']
    )
    assert n1t1['name'] == n1t2['name'] == n1t3['name'] == 'Test Gene 123'
    assert (
        n1t1['description']
        == n1t2['description']
        == n1t3['description']
        == 'This is a Test Gene 123'
    )
    assert (
        'Test Dataset' in n1t1['provided_by']
        and 'Test Dataset' in n1t2['provided_by']
        and 'Test Dataset' in n1t3['provided_by']
    )


def test_rdf_transform4():
    """
    Test parsing an RDF N-triple and round-trip, with user defined node property predicates.
    """
    node_property_predicates = {
        f"https://www.example.org/UNKNOWN/{x}"
        for x in ['fusion', 'homology', 'combined_score', 'cooccurence']
    }
    input_args1 = {
        'filename': [os.path.join(RESOURCE_DIR, 'rdf', 'test2.nt')],
        'format': 'nt',
        'node_property_predicates': node_property_predicates,
    }
    t1 = Transformer()
    t1.transform(input_args1)
    assert t1.store.graph.number_of_nodes() == 4
    assert t1.store.graph.number_of_edges() == 3

    output_args2 = {'filename': os.path.join(TARGET_DIR, 'test2-export.nt'), 'format': 'nt'}
    t1.save(output_args2)

    t2 = Transformer()
    input_args2 = {'filename': [os.path.join(TARGET_DIR, 'test2-export.nt')], 'format': 'nt'}
    t2.transform(input_args2)
    assert t2.store.graph.number_of_nodes() == 4
    assert t2.store.graph.number_of_edges() == 3

    n1t1 = t1.store.graph.nodes()['ENSEMBL:ENSG0000000000001']
    n1t2 = t2.store.graph.nodes()['ENSEMBL:ENSG0000000000001']

    assert n1t1['type'] == n1t2['type'] == 'SO:0000704'
    assert len(n1t1['category']) == len(n1t2['category']) == 4
    assert 'biolink:Gene' in n1t1['category'] and 'biolink:Gene' in n1t2['category']
    assert (
        'biolink:GenomicEntity' in n1t1['category'] and 'biolink:GenomicEntity' in n1t2['category']
    )
    assert 'biolink:NamedThing' in n1t1['category'] and 'biolink:NamedThing' in n1t2['category']
    assert n1t1['name'] == n1t2['name'] == 'Test Gene 123'
    assert n1t1['description'] == n1t2['description'] == 'This is a Test Gene 123'
    assert 'Test Dataset' in n1t1['provided_by'] and 'Test Dataset' in n1t2['provided_by']

    e1t1 = list(
        t1.store.graph.get_edge('ENSEMBL:ENSP0000000000001', 'ENSEMBL:ENSP0000000000002').values()
    )[0]
    e1t2 = list(
        t2.store.graph.get_edge('ENSEMBL:ENSP0000000000001', 'ENSEMBL:ENSP0000000000002').values()
    )[0]

    assert e1t1['subject'] == e1t2['subject'] == 'ENSEMBL:ENSP0000000000001'
    assert e1t1['object'] == e1t2['object'] == 'ENSEMBL:ENSP0000000000002'
    assert e1t1['predicate'] == e1t2['predicate'] == 'biolink:interacts_with'
    assert e1t1['relation'] == e1t2['relation'] == 'biolink:interacts_with'
    assert e1t1['type'] == e1t2['type'] == 'biolink:Association'
    assert e1t1['id'] == e1t2['id'] == 'urn:uuid:fcf76807-f909-4ccb-b40a-3b79b49aa518'
    assert e1t1['fusion'] == e1t2['fusion'] == '0'
    assert e1t1['homology'] == e1t2['homology'] == '0.0'
    assert e1t1['combined_score'] == e1t2['combined_score'] == '490.0'
    assert e1t1['cooccurence'] == e1t2['cooccurence'] == '332'


def test_rdf_transform5():
    """
    Parse an RDF N-Triple and round-trip, with user defined node property predicates
    and export property types.
    """
    node_property_predicates = {
        f"https://www.example.org/UNKNOWN/{x}"
        for x in ['fusion', 'homology', 'combined_score', 'cooccurence']
    }
    property_types = {}
    for k in node_property_predicates:
        property_types[k] = 'xsd:float'

    input_args1 = {
        'filename': [os.path.join(RESOURCE_DIR, 'rdf', 'test3.nt')],
        'format': 'nt',
        'node_property_predicates': node_property_predicates,
    }
    t1 = Transformer()
    t1.transform(input_args1)
    assert t1.store.graph.number_of_nodes() == 7
    assert t1.store.graph.number_of_edges() == 6

    output_args2 = {
        'filename': os.path.join(TARGET_DIR, 'test3-export.nt'),
        'format': 'nt',
        'property_types': property_types,
    }
    t1.save(output_args2)

    input_args2 = {'filename': [os.path.join(TARGET_DIR, 'test3-export.nt')], 'format': 'nt'}
    t2 = Transformer()
    t2.transform(input_args2)
    assert t2.store.graph.number_of_nodes() == 7
    assert t2.store.graph.number_of_edges() == 6

    n1t1 = t1.store.graph.nodes()['ENSEMBL:ENSG0000000000001']
    n1t2 = t2.store.graph.nodes()['ENSEMBL:ENSG0000000000001']

    assert n1t1['type'] == n1t2['type'] == 'SO:0000704'
    assert len(n1t1['category']) == len(n1t2['category']) == 4
    assert 'biolink:Gene' in n1t1['category'] and 'biolink:Gene' in n1t2['category']
    assert (
        'biolink:GenomicEntity' in n1t1['category'] and 'biolink:GenomicEntity' in n1t2['category']
    )
    assert 'biolink:NamedThing' in n1t1['category'] and 'biolink:NamedThing' in n1t2['category']
    assert n1t1['name'] == n1t2['name'] == 'Test Gene 123'
    assert n1t1['description'] == n1t2['description'] == 'This is a Test Gene 123'
    assert 'Test Dataset' in n1t1['provided_by'] and 'Test Dataset' in n1t2['provided_by']

    e1t1 = list(
        t1.store.graph.get_edge('ENSEMBL:ENSP0000000000001', 'ENSEMBL:ENSP0000000000002').values()
    )[0]
    e1t2 = list(
        t2.store.graph.get_edge('ENSEMBL:ENSP0000000000001', 'ENSEMBL:ENSP0000000000002').values()
    )[0]

    assert e1t1['subject'] == e1t2['subject'] == 'ENSEMBL:ENSP0000000000001'
    assert e1t1['object'] == e1t2['object'] == 'ENSEMBL:ENSP0000000000002'
    assert e1t1['predicate'] == e1t2['predicate'] == 'biolink:interacts_with'
    assert e1t1['relation'] == e1t2['relation'] == 'biolink:interacts_with'
    assert e1t1['type'] == e1t2['type'] == 'biolink:Association'
    assert e1t1['id'] == e1t2['id'] == 'urn:uuid:fcf76807-f909-4ccb-b40a-3b79b49aa518'
    assert e1t2['fusion'] == 0.0
    assert e1t2['homology'] == 0.0
    assert e1t2['combined_score'] == 490.0
    assert e1t2['cooccurence'] == 332.0


def test_transform_inspector():
    """
    Test transform with an inspection callable.
    """
    input_args = {
        'filename': [
            os.path.join(RESOURCE_DIR, 'test2_nodes.tsv'),
            os.path.join(RESOURCE_DIR, 'test2_edges.tsv'),
        ],
        'format': 'tsv',
    }
    t = Transformer()

    class TestInspector:
        def __init__(self):
            self._node_count = 0
            self._edge_count = 0

        def __call__(self, rec: List):
            if len(rec) == 4:  # infer an edge record
                self._edge_count += 1
            else:
                self._node_count += 1

        def get_node_count(self):
            return self._node_count

        def get_edge_count(self):
            return self._edge_count

    inspector = TestInspector()
    t.transform(input_args=input_args, inspector=inspector)

    assert inspector.get_node_count() == 4
    assert inspector.get_edge_count() == 4
