# dzpokerV3/tests/test_hand_evaluator.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.cards import Card
from core.hand_evaluator import evaluate_hand, find_winners

class TestHandEvaluator(unittest.TestCase):

    def test_evaluate_hand_placeholder(self):
        """
        Test the placeholder hand evaluation logic.
        NOTE: This test will need to be updated when a real evaluator is implemented.
        """
        # Test case 1: A simple high card hand
        hole = [Card('A', 'H'), Card('K', 'D')]
        community = [Card('2', 'S'), Card('4', 'C'), Card('6', 'H'), Card('8', 'D'), Card('T', 'S')]
        score, hand, _ = evaluate_hand(hole, community)
        self.assertIsInstance(score, int)
        self.assertEqual(len(hand), 5)
        # Placeholder logic just checks for high card sum, so A,K,T,8,6 should be the hand
        self.assertEqual(sorted([c.rank for c in hand]), sorted(['A', 'K', 'T', '8', '6']))

    def test_evaluate_one_pair(self):
        """Test the placeholder logic for detecting one pair."""
        hole = [Card('A', 'H'), Card('A', 'D')]
        community = [Card('2', 'S'), Card('4', 'C'), '6', 'H', '8', 'D', 'T', 'S'] # Should be Card objects
        community_cards = [Card('2', 'S'), Card('4', 'C'), Card('6', 'H'), Card('8', 'D'), Card('T', 'S')]
        score, hand, _ = evaluate_hand(hole, community_cards)
        # The placeholder logic adds a bonus for a pair, so this score should be higher than a non-pair hand
        hole_high = [Card('K', 'H'), Card('Q', 'D')]
        score_high, _, _ = evaluate_hand(hole_high, community_cards)
        self.assertGreater(score, score_high)

    def test_find_winners_single_winner(self):
        """Test finding a single winner from a showdown."""
        # p2 makes three of a kind (Kings), which beats p1's pair of Aces.
        game_state = {
            'community_cards': [Card('2', 'S'), Card('5', 'C'), Card('J', 'H'), Card('Q', 'D'), Card('K', 'S')],
            'players': {
                'p1': {'is_in_hand': True, 'hole_cards': [Card('A', 'H'), Card('A', 'S')]}, # One pair (Aces)
                'p2': {'is_in_hand': True, 'hole_cards': [Card('K', 'H'), Card('K', 'C')]}, # Three of a kind (Kings)
                'p3': {'is_in_hand': True, 'hole_cards': [Card('T', 'C'), Card('9', 'C')]}  # High card
            }
        }
        winners = find_winners(game_state)
        self.assertEqual(winners, ['p2'])

    def test_find_winners_split_pot(self):
        """Test finding multiple winners (split pot) in a showdown."""
        # The best possible hand is on the board (e.g. a high pair).
        # Both players must play the board, resulting in a split pot as their hole cards don't improve their hand.
        game_state = {
            'community_cards': [Card('A', 'S'), Card('A', 'C'), Card('K', 'H'), Card('Q', 'D'), Card('J', 'S')],
            'players': {
                'p1': {'is_in_hand': True, 'hole_cards': [Card('2', 'H'), Card('3', 'S')]}, # Plays the board
                'p2': {'is_in_hand': True, 'hole_cards': [Card('2', 'C'), Card('4', 'D')]}, # Plays the board
                'p3': {'is_in_hand': True, 'hole_cards': [Card('T', 'H'), Card('9', 'C')]}  # Plays the board
            }
        }
        winners = find_winners(game_state)
        # p1 and p2 should tie because their best 5-card hand is exactly the same (the board)
        # and their high card scores will be identical.
        self.assertCountEqual(winners, ['p1', 'p2', 'p3'])


    def test_find_winner_by_fold(self):
        """Test that the last remaining player wins if everyone else folds."""
        game_state = {
            'community_cards': [],
            'players': {
                'p1': {'is_in_hand': False, 'last_action': 'FOLD'},
                'p2': {'is_in_hand': True},
                'p3': {'is_in_hand': False, 'last_action': 'FOLD'}
            }
        }
        winners = find_winners(game_state)
        self.assertEqual(winners, ['p2'])

if __name__ == '__main__':
    unittest.main()
