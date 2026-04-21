"""V3 — Print-friendly style pass: large fonts, minimal colour, clean typography."""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.flowchart import Action, Decision, Document

graph_attr = {
    "splines": "ortho",
    "nodesep": "0.8",
    "ranksep": "1.3",
    "fontsize": "22",
    "fontname": "Helvetica-Bold",
    "pad": "0.6",
    "bgcolor": "white",
}
node_attr = {
    "fontsize": "16",
    "fontname": "Helvetica",
    "style": "filled",
    "fillcolor": "gray95",
    "color": "black",
    "penwidth": "1.6",
}
edge_attr = {
    "fontsize": "14",
    "fontname": "Helvetica",
    "color": "black",
    "penwidth": "1.3",
}
cluster_attr = {
    "fontsize": "16",
    "fontname": "Helvetica-Bold",
    "style": "rounded",
    "color": "gray40",
    "bgcolor": "gray95",
}

with Diagram(
    "Contrastive Plan Comparison",
    filename="architecture_diagram_v3_print",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    with Cluster("Input", graph_attr=cluster_attr):
        problem = Document("Planning\nProblem")
        question = Document("Contrastive\nQuestion")

    with Cluster("Constraint Compilation", graph_attr=cluster_attr):
        encode = Action("Encode as\nPDDL fragment")

    with Cluster("Planning", graph_attr=cluster_attr):
        planner_o = Action("Planner\n(original)")
        planner_m = Action("Planner\n(modified)")

    with Cluster("Comparison", graph_attr=cluster_attr):
        diff = Decision("Plan Diff")
        output = Document("Explanation")

    problem >> planner_o
    problem >> encode
    question >> encode
    encode >> planner_m

    planner_o >> Edge(label="π") >> diff
    planner_m >> Edge(label="π'") >> diff
    diff >> output
