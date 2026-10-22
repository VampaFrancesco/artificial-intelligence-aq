import json
from ..models.node import Node


def load_location(file_path):
    with open(file_path,'r') as f:
        data = json.load(f)

    depot = Node(
            x = data['depot']['x'],
            y = data['depot']['y']
    )

    locations = [depot]

    for delivery in data['deliveries']:
        node = Node(
                x = delivery['x'],
                y = delivery['y']
        )
        locations.append(node)

    return locations