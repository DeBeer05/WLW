import threading
import time

def main():
    bar = Loading("Loading")
    bar.start_loading()
    time.sleep(5)
    bar.stop_loading()
    time.sleep(5)




class Loading:
    def __init__(self, title:str) -> None:
        self.title = title
        self._loading_bussy = False
       


    def start_loading(self):
        self._loading_bussy = True
        loader_thread = threading.Thread(target=self.load, daemon=True)
        loader_thread.start()

    def stop_loading(self):
        self._loading_bussy = False


    def load(self):
        frames = ['/', '-', '\\', '|']
        i = 0
        while self._loading_bussy:
            print(f'{frames[i]} {self.title} {frames[i]}\r', end='')
            i += 1
            if i > len(frames) - 1:
                i = 0
            time.sleep(0.3)

        

if __name__ == '__main__':
    main()