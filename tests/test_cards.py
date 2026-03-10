# dzpokerV3/tests/test_cards.py
import unittest
import sys
import os

# Add the parent directory to the Python path to allow module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.cards import Card, Deck, SUITS, RANKS

class TestCards(unittest.TestCase):

    def test_card_creation(self):
        """Test that a card is created with the correct rank and suit."""
        card = Card('A', 'S')
        self.assertEqual(card.rank, 'A')
        self.assertEqual(card.suit, 'S')
        self.assertEqual(str(card), 'AS')

    def test_invalid_card(self):
        """Test that creating an invalid card raises a ValueError."""
        with self.assertRaises(ValueError):
            Card('X', 'S') # Invalid rank
        with self.assertRaises(ValueError):
            Card('A', 'Z') # Invalid suit

    def test_deck_creation(self):
        """Test that a new deck has 52 unique cards."""
        deck = Deck()
        self.assertEqual(len(deck), 52)
        # Check for uniqueness
        self.assertEqual(len(set(str(c) for c in deck.cards)), 52)

    def test_deck_shuffle(self):
        """Test that shuffling changes the order of cards."""
        deck1 = Deck()
        deck2 = Deck()
        # The probability of two shuffles being the same is astronomically low.
        self.assertNotEqual([str(c) for c in deck1.cards], [str(c) for c in deck2.cards])

    def test_deck_draw_one(self):
        """Test drawing a single card from the deck."""
        deck = Deck()
        top_card_str = str(deck.cards[-1])
        drawn_card = deck.draw()
        self.assertEqual(len(deck), 51)
        self.assertIsInstance(drawn_card, Card)
        self.assertEqual(str(drawn_card), top_card_str)

    def test_deck_draw_multiple(self):
        """Test drawing multiple cards from the deck."""
        deck = Deck()
        top_cards_strs = [str(c) for c in deck.cards[-3:]]
        drawn_cards = deck.draw(3)
        self.assertEqual(len(deck), 49)
        self.assertEqual(len(drawn_cards), 3)
        self.assertEqual([str(c) for c in drawn_cards], list(reversed(top_cards_strs)))

    def test_deck_draw_too_many(self):
        """Test that drawing more cards than available raises a ValueError."""
        deck = Deck()
        with self.assertRaises(ValueError):
            deck.draw(53)

if __name__ == '__main__':
    unittest.main()
