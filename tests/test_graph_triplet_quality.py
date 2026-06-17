from app.ingestion.graph_extractor import GraphTriplet, filter_triplets


def test_filter_triplets_drops_low_confidence():
    rows = [
        GraphTriplet(head="A", relation="USES", tail="B", confidence=0.91, method="llm"),
        GraphTriplet(head="A", relation="RELATED_TO", tail="Thing", confidence=0.25, method="rules"),
    ]

    kept = filter_triplets(rows, min_confidence=0.5)

    assert len(kept) == 1
    assert kept[0].relation == "USES"


def test_filter_triplets_dedupes_same_edge():
    rows = [
        GraphTriplet(head="A", relation="USES", tail="B", confidence=0.70, method="rules"),
        GraphTriplet(head="A", relation="USES", tail="B", confidence=0.95, method="llm"),
    ]

    kept = filter_triplets(rows, min_confidence=0.5)

    assert len(kept) == 1
    assert kept[0].confidence == 0.95
