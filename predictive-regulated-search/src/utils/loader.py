import json
from math import isfinite
from ..models.node import Node


def load_location(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get('deliveries'), list):
        raise ValueError('Il file deve contenere depot e una lista deliveries.')

    def read_node(point, label):
        if not isinstance(point, dict) or any(
            isinstance(point.get(axis), bool)
            or not isinstance(point.get(axis), (int, float))
            or not isfinite(point[axis]) for axis in ('x', 'y')
        ):
            raise ValueError(f'{label}: x e y devono essere numeri finiti.')
        return Node(x=point['x'], y=point['y'])

    return [read_node(data.get('depot'), 'Deposito')] + [
        read_node(point, f'Consegna {number}')
        for number, point in enumerate(data['deliveries'], 1)
    ]
