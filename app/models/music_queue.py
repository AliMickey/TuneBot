from collections import deque

class MusicQueue:
    """Handles the music queue for a guild."""
    def __init__(self):
        self.queue = deque()
        self.current = None
        self.loop = False
        self.volume = 1.0
        self.processing = True
        self.pending_tracks = []
        self.shuffle_count = 0
        self.track_info = {}

    def add_track(self, track):
        """Add a track to the queue."""
        self.queue.append(track)

    def pop_left(self):
        """Remove and return the leftmost item."""
        return self.queue.popleft() if self.queue else None
        
    def pop_at(self, index):
        """Remove and return item at index."""
        if not self.queue or index >= len(self.queue):
            return None
        temp_list = list(self.queue)
        item = temp_list.pop(index)
        self.queue = deque(temp_list)
        return item

    def clear(self):
        """Clear the queue."""
        self.queue.clear()

    def get_length(self):
        """Get queue length."""
        return len(self.queue)
