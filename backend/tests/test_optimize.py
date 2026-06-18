from app.services.optimize import optimize_order, path_cost


def test_two_opt_improves_obvious_crossing():
    # 4 points on a line at x=0,1,2,3 but given out of order; optimal is 0-1-2-3.
    coords = [0.0, 2.0, 1.0, 3.0]
    n = len(coords)
    cost = [[abs(coords[i] - coords[j]) for j in range(n)] for i in range(n)]
    order = optimize_order(cost, start=0)
    assert path_cost(order, cost) <= path_cost([0, 1, 2, 3], cost)
    assert sorted(order) == [0, 1, 2, 3]  # a valid permutation


def test_trivial_sizes():
    assert optimize_order([[0.0]]) == [0]
    assert optimize_order([[0.0, 1.0], [1.0, 0.0]]) == [0, 1]
