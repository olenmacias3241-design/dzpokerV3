# dzpokerV3/core/cards.py
import random

SUITS = ['H', 'D', 'C', 'S']  # Hearts, Diamonds, Clubs, Spades
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

class Card:
    """ Represents a single playing card. """
    def __init__(self, rank, suit):
        if rank not in RANKS or suit not in SUITS:
            raise ValueError(f"Invalid card: {rank}{suit}")
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def to_str(self):
        """ Returns the string representation of the card, e.g., 'AH' for Ace of Hearts. """
        return f"{self.rank}{self.suit}"

class Deck:
    """ Represents a deck of 52 playing cards. """
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        self.shuffle()

    def shuffle(self):
        """ Shuffles the deck. """
        random.shuffle(self.cards)

    def draw(self, n=1):
        """ Draws n cards from the top of the deck. """
        if n > len(self.cards):
            raise ValueError("Cannot draw more cards than are in the deck.")
        if n == 1:
            return self.cards.pop()
        
        drawn_cards = self.cards[-n:]
        self.cards = self.cards[:-n]
        drawn_cards.reverse() # Reverse to simulate popping one by one
        return drawn_cards

    def __len__(self):
        return len(self.cards)

    def __repr__(self):
        return f"Deck of {len(self.cards)} cards"

if __name__ == '__main__':
    # --- Test ---
    deck = Deck()
    print(f"Created a new shuffled deck: {deck}")
    
    # Draw hole cards for 2 players
    player1_hand = deck.draw(2)
    player2_hand = deck.draw(2)
    print(f"Player 1's hand: {player1_hand}")
    print(f"Player 2's hand: {player2_hand}")
    print(f"Cards remaining in deck: {len(deck)}")

    # Deal the flop
    flop = deck.draw(3)
    print(f"Flop: {flop}")
    print(f"Cards remaining in deck: {len(deck)}")

    # Deal the turn
    turn = deck.draw(1)
    print(f"Turn: {turn}")
    print(f"Cards remaining in deck: {len(deck)}")

    # Deal the river
    river = deck.draw(1)
    print(f"River: {river}")
    print(f"Cards remaining in deck: {len(deck)}")
