# visualize.py

from test import create_main_graph

def visualize_graph():
    main_graph = create_main_graph()
    try:
        # Generate the graph visualization using Mermaid
        graph_visual = main_graph.graph.get_graph(xray=1)
        image_data = graph_visual.draw_mermaid_png()

        # Save the image to a file
        with open('output_graph.png', 'wb') as f:
            f.write(image_data)
        print("Image saved as output_graph.png")
    except Exception as e:
        print(f"An error occurred during visualization: {e}")

if __name__ == "__main__":
    visualize_graph()
