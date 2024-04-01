def individual_serial_Players(Players) -> dict:
    return {
        'id': str(Players['_id']) if '_id' in Players else None,
        "playerName": Players["playerName"],
        "playerAge": Players["playerAge"],
        "playerHeight": Players["playerHeight"],
        "playerWeight": Players["playerWeight"]
    }    

def list_serial_Players(Players) -> list:
    return [individual_serial_Players(player) for player in Players]