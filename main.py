from block import State

__author__ = 'alexisgallepe'

import time
import peers_manager
import pieces_manager
import torrent
import tracker
import logging
import os
import message

no_unchoke_time=0

class Run(object):
    percentage_completed = -1
    last_log_line = ""

    def __init__(self):
        self.torrent = torrent.Torrent().load_from_path("torrent.torrent")
        self.tracker = tracker.Tracker(self.torrent)

        self.pieces_manager = pieces_manager.PiecesManager(self.torrent)
        self.peers_manager = peers_manager.PeersManager(self.torrent, self.pieces_manager)

        self.peers_manager.start()
        logging.info("PeersManager Started")
        logging.info("PiecesManager Started")

    # def restart(self):
    #     logging.info("Я рестартую")
    #
    #     peers_dict = self.tracker.get_peers_from_trackers(True)
    #     self.peers_manager.add_peers(peers_dict.values())

    def restart_peer(self):
        peers_dict = self.tracker.get_peers_from_trackers(True)
        # self.peers_manager.add_peers(peers_dict.values())

    def start(self):
        global no_unchoke_time
        peers_dict = self.tracker.get_peers_from_trackers(alonepeer=False)
        self.peers_manager.add_peers(peers_dict.values(),alonepeer=False)

        while not self.pieces_manager.all_pieces_completed():
            broken_peer = self.peers_manager.has_no_unchoked_peers()
            if broken_peer != None:
                no_unchoke_time+=1
                if no_unchoke_time > 5:
                    # self.restart_peer()
                    no_unchoke_time=0
                    if not self.peers_manager.has_unchoked_peers():
                        logging.error("I am broked...")
                continue

            for piece in self.pieces_manager.pieces:
                index = piece.piece_index

                if self.pieces_manager.pieces[index].is_full:
                    continue

                peer = self.peers_manager.get_random_peer_having_piece(index)
                if not peer:
                    continue

                self.pieces_manager.pieces[index].update_block_status()

                data = self.pieces_manager.pieces[index].get_empty_block()
                if not data:
                    continue

                piece_index, block_offset, block_length = data
                piece_data = message.Request(piece_index, block_offset, block_length).to_bytes()
                peer.send_to_peer(piece_data)

            self.display_progression()

            time.sleep(0.1)

        logging.info("File(s) downloaded successfully.")
        self.display_progression()

        self._exit_threads()

    def display_progression(self):
        new_progression = 0

        for i in range(self.pieces_manager.number_of_pieces):
            for j in range(self.pieces_manager.pieces[i].number_of_blocks):
                if self.pieces_manager.pieces[i].blocks[j].state == State.FULL:
                    new_progression += len(self.pieces_manager.pieces[i].blocks[j].data)

        if new_progression == self.percentage_completed:
            return

        number_of_peers = self.peers_manager.unchoked_peers_count()
        percentage_completed = float((float(new_progression) / self.torrent.total_length) * 100)

        current_log_line = "Connected peers: {} - {}% completed | {}/{} pieces".format(number_of_peers,
                                                                                         round(percentage_completed, 2),
                                                                                         self.pieces_manager.complete_pieces,
                                                                                         self.pieces_manager.number_of_pieces)
        if current_log_line != self.last_log_line:
            print(current_log_line)

        self.last_log_line = current_log_line
        self.percentage_completed = new_progression

    def _exit_threads(self):
        self.peers_manager.is_active = False
        os._exit(0)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    run = Run()
    run.start()
