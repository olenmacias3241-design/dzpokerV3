# dzpokerV3/api_events.py

from flask_socketio import emit, join_room, leave_room
from flask import request

# This is a bit of a trick: we're defining the event handlers in this file,
# but the `socketio` object will be initialized in app.py.
# We'll import this file into app.py and the handlers will be registered.
# To make this work, we need a way to get the `socketio` object.
# A common pattern is to use a "factory" function or an app context,
# but for simplicity here, we will assume a global `socketio` object
# is available after being initialized in app.py.

# We need to import the app and socketio objects from the main app file
# To avoid circular imports, we'll do it carefully.
from app import socketio, game

# --- Client -> Server Event Handlers ---

@socketio.on('connect')
def handle_connect():
    """Handles a new client connection."""
    # For now, all players join a single "main_table" room.
    # In a real app, this would be dynamic based on the table they choose.
    join_room('main_table')
    print(f"Client {request.sid} connected and joined main_table")
    # Send the current game state to the newly connected player
    emit('game:state_update', game.get_state(private_for_player_sid=request.sid), room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    """Handles a client disconnection."""
    leave_room('main_table')
    print(f"Client {request.sid} disconnected")
    # Here you might want to handle removing the player from the game if they disconnect.

@socketio.on('game:action')
def handle_game_action(data):
    """
    Handles a player's game action (fold, check, call, bet, raise).
    Payload: { action: string, amount: number }
    """
    player_sid = request.sid
    # Note: In a real app, you need a mapping from sid to player object.
    # For this example, we'll assume we can find the player.
    player = game.get_player_by_sid(player_sid) # This function needs to be implemented in core/logic.py

    if not player or not game.is_players_turn(player):
        emit('error', {'message': 'Not your turn or player not found.'}, room=player_sid)
        return

    action = data.get('action')
    amount = data.get('amount', 0)

    # --- Game Logic Integration ---
    # This is where you call your core game logic.
    # The game logic should validate the move and update the game state.
    # e.g., game.perform_action(player, action, amount)
    # -----------------------------
    
    print(f"Received action from {player.name}: {action} {amount}")
    # After the action, the game state changes. We need to broadcast the new state.
    broadcast_game_state()

@socketio.on('game:leave_table')
def handle_leave_table():
    """Handles a player leaving the table."""
    player_sid = request.sid
    player = game.get_player_by_sid(player_sid)
    if player:
        game.remove_player(player)
        print(f"Player {player.name} left the table.")
        # Broadcast the new state to all remaining players
        broadcast_game_state()

@socketio.on('game:chat_message')
def handle_chat_message(data):
    """Handles incoming chat messages and broadcasts them."""
    player = game.get_player_by_sid(request.sid)
    message = data.get('message')
    if player and message:
        emit('game:new_chat', {
            'sender': player.name,
            'message': message
        }, room='main_table')

# --- Helper Functions for Server -> Client Emits ---

def broadcast_game_state():
    """
    Broadcasts the current game state to all players in the room.
    It sends a generic state to the room and private states (with hole cards) to each player.
    """
    # Broadcast public state to everyone
    emit('game:state_update', game.get_state(), room='main_table', broadcast=True)
    
    # Send private states to each player individually
    for player in game.players:
        if player.sid: # Check if the player has a session ID
            emit('game:state_update', game.get_state(private_for_player_sid=player.sid), room=player.sid)

def deal_hole_cards(player, cards):
    """Emits the private hole cards to a specific player."""
    if player.sid:
        emit('private:deal_hole_cards', {'cards': cards}, room=player.sid)

