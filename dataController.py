from typing import Callable, List, Awaitable
from clock import TimeController
from db import Database

class ModelMachine:
    def __init__(self, name: str,
                 callback: Callable[[List[float], List[float], List[float], str], Awaitable[None]],
                 batch_size: int = 10):
        self.vib_left = []
        self.vib_right = []
        self.temp = []
        self.batch_size = batch_size
        self.callback = callback
        self.name = name

    async def trigger(self):
        if self.is_batch():
            await self.callback(self.vib_left[:self.batch_size], self.vib_right[:self.batch_size],
                                self.temp[:self.batch_size], self.name)

            self.clear_batch()

    def is_batch(self):
        return len(self.vib_left) >= self.batch_size \
            and len(self.temp) >= self.batch_size \
            and len(self.vib_right) >= self.batch_size

    def clear_batch(self):
        del self.vib_left[:self.batch_size]
        del self.vib_right[:self.batch_size]
        del self.temp[:self.batch_size]

    def add_vib_left(self, data):
        self.vib_left.extend(data)

    def add_vib_right(self, data):
        self.vib_right.extend(data)

    async def add_vib(self, left_data, right_data):
        self.add_vib_left(left_data)
        self.add_vib_right(right_data)
        await self.trigger()

    async def add_temp(self, data):
        self.temp.extend(data)
        await self.trigger()


class StatModel:
    def __init__(self, name, db: Database):
        self.name = name
        self.left = Statistics()
        self.right = Statistics()
        self.temp = Statistics()
        self.time = TimeController()
        self.db = db

    async def callback(self):
        self.db.save_now(self.left.get_average())

    async def trigger(self):
        is_hour_changed = self.time.is_hour_change()
        if is_hour_changed:
            await self.callback()

    async def add_vib(self, left_data, right_data):
        self.left.add(left_data)
        self.right.add(right_data)
        await self.trigger()

    async def add_temp(self, datas):
        self.temp.add(datas)
        await self.trigger()


class Statistics:
    def __init__(self):
        self.data_sum = 0
        self.size = 0

    def add(self, datas):
        self.data_sum += sum(abs(datas))
        self.size += len(datas)

    def reset(self):
        self.data_sum = 0
        self.size = 0

    def get_average(self):
        average = self.data_sum / self.size
        self.reset()

        return average


class DataController:
    def __init__(self, model_req: Callable[[List[float], List[float], List[float]], Awaitable[None]], batch_size,
                 sampling_rate: int):
        self.machine1 = ModelMachine('machine1', model_req, batch_size)
        self.machine2 = ModelMachine('machine2', model_req, batch_size)
        self.sampling_rate = sampling_rate

    async def add_vib(self, message: dict):
        await self.machine1.add_vib(message['machine1_left'], message['machine1_right'])
        await self.machine2.add_vib(message['machine2_left'], message['machine2_right'])

    async def add_temp(self, message: dict):
        await self.machine1.add_temp(message['machine1'])
        await self.machine2.add_temp(message['machine2'])
