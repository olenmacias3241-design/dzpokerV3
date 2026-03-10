# dzpokerV3/tests/test_game_logic.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.game_logic import (
    GameStage, PlayerAction, handle_player_action, start_new_hand, advance_to_next_stage
)

class TestGameLogic(unittest.TestCase):

    def setUp(self):
        """Set up a mock game state for each test."""
        self.mock_game_state = {
            'sb': 5,
            'bb': 10,
            'pot': 0,
            'community_cards': [],
            'dealer_button_position': 0,
            'players': {
                'p1': {'stack': 1000, 'is_in_hand': True, 'bet_this_round': 0}, # Button
                'p2': {'stack': 1000, 'is_in_hand': True, 'bet_this_round': 0}, # SB
                'p3': {'stack': 1000, 'is_in_hand': True, 'bet_this_round': 0}, # BB
            },
            'deck': None,
            'current_player_id': None,
            'amount_to_call': 0,
            'last_raiser_id': None,
        }

    def test_start_new_hand(self):
        """Test the initialization of a new hand."""
        state = start_new_hand(self.mock_game_state)
        
        # Test blind posting
        self.assertEqual(state['players']['p2']['stack'], 1000 - 5)
        self.assertEqual(state['players']['p2']['bet_this_round'], 5)
        self.assertEqual(state['players']['p3']['stack'], 1000 - 10)
        self.assertEqual(state['players']['p3']['bet_this_round'], 10)
        self.assertEqual(state['pot'], 15)
        self.assertEqual(state['amount_to_call'], 10)
        
        # Test card dealing
        self.assertEqual(len(state['deck']), 52 - (3 * 2)) # 3 players * 2 cards
        self.assertEqual(len(state['players']['p1']['hole_cards']), 2)
        
        # Test first player to act (UTG, which is p1 in this 3-player setup)
        self.assertEqual(state['current_player_id'], 'p1')

    def test_player_action_fold(self):
        """Test a player folding."""
        state = start_new_hand(self.mock_game_state)
        state, err = handle_player_action(state, 'p1', PlayerAction.FOLD)
        
        self.assertIsNone(err)
        self.assertFalse(state['players']['p1'].get('is_active')) # Should be marked inactive
        self.assertEqual(state['current_player_id'], 'p2') # Action moves to the next player

    def test_player_action_call(self):
        """Test a player calling."""
        state = start_new_hand(self.mock_game_state) # p1 is to act, needs to call 10
        state, err = handle_player_action(state, 'p1', PlayerAction.CALL, 10)

        self.assertIsNone(err)
        self.assertEqual(state['players']['p1']['stack'], 1000 - 10)
        self.assertEqual(state['players']['p1']['bet_this_round'], 10)
        self.assertEqual(state['pot'], 15 + 10)
        self.assertEqual(state['current_player_id'], 'p2') # Action moves to SB

    def test_player_action_raise(self):
        """Test a player raising."""
        state = start_new_hand(self.mock_game_state)
        state, err = handle_player_action(state, 'p1', PlayerAction.RAISE, 20) # Raise to total 30
        
        # The 'amount' for RAISE is the additional amount *on top of* the call amount.
        # So, call 10 + raise 20 = 30 total bet.
        
        self.assertIsNone(err)
        self.assertEqual(state['players']['p1']['stack'], 1000 - 30)
        self.assertEqual(state['players']['p1']['bet_this_round'], 30)
        self.assertEqual(state['pot'], 15 + 30)
        self.assertEqual(state['amount_to_call'], 30)
        self.assertEqual(state['last_raiser_id'], 'p1')
        self.assertEqual(state['current_player_id'], 'p2')

    def test_end_of_preflop_round(self):
        """Test the full pre-flop betting round ending correctly."""
        state = start_new_hand(self.mock_game_state)
        state, _ = handle_player_action(state, 'p1', PlayerAction.CALL, 10) # p1 calls 10
        state, _ = handle_player_action(state, 'p2', PlayerAction.CALL, 5)  # p2 (SB) calls 5 to complete 10
        state, _ = handle_player_action(state, 'p3', PlayerAction.CHECK) # p3 (BB) can check
        
        # The last action by p3 should have ended the round and advanced the stage
        self.assertEqual(state['stage'], GameStage.FLOP)
        self.assertEqual(len(state['community_cards']), 3)
        self.assertEqual(state['pot'], 30)
        # Action should now start with the first active player after the button (SB, which is p2)
        self.assertEqual(state['current_player_id'], 'p2')
        self.assertEqual(state['amount_to_call'], 0) # Betting reset for the new round
        self.assertEqual(state['players']['p1']['bet_this_round'], 0) # bet_this_round is reset


if __name__ == '__main__':
    unittest.main()
