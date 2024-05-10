#!/usr/bin/env python3
"""
Copyright 2024 Joe Maples <joe@maples.dev>

This file is part of OpenQ1Display.

OpenQ1Display is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

OpenQ1Display is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
OpenQ1Display. If not, see <https://www.gnu.org/licenses/>. 
"""

import asyncio
import logging

from nextion import TJC, EventType
from setproctitle import setproctitle
from typing import List

from .utils import SimpleDict
from .config import *
from .printer import Printer, PrinterStatus
from .pages.base_page import BasePage


class State:
    def __init__(self):
        self.options: Config
        self.display: TJC
        self.printer: Printer
        self.printerData: dict = {}
        self.fileList: dict = {}
        self.backstack: List[BasePage] = []

    def currentPage(self) -> BasePage:
        return self.backstack[-1]


class OpenQ1Display:
    def __init__(self):
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.DEBUG,
            handlers=[logging.StreamHandler()],
        )
        self.pages = self.registerPages()
        self.state: State = State()
        self.state.options = Config(getConfigPath())
        self.state.display = TJC(
            self.state.options[TABLE_DISPLAY][KEY_DEVICE],
            self.state.options[TABLE_DISPLAY][KEY_BAUD],
            self.onDisplayEvent,
        )
        self.state.printer = Printer(
            self.state.options,
            self.onConnectionEvent,
            self.onPrinterStatusUpdate,
            self.onFileListUpdate,
        )

    def registerPages(self) -> SimpleDict:
        pages = SimpleDict()
        # pages[BasePage.name] = BasePage

        return pages

    async def onDisplayEvent(self, type: EventType, data):
        logging.debug("Display: Event %s data: %s", type, str(data))
        logging.debug("Passing event to page %s", self.state.currentPage().name)
        asyncio.create_task(self.state.currentPage().onDisplayEvent(type, data))

    async def onConnectionEvent(self, status: PrinterStatus):
        logging.info("Conenction status: %s", status)
        if status == PrinterStatus.NOT_READY:
            asyncio.create_task(self.changePage("boot"))
            pass
        elif status == PrinterStatus.READY:
            asyncio.create_task(self.changePage("main"))
            pass
        elif status == PrinterStatus.STOPPED:
            pass
        elif status == PrinterStatus.MOONRAKER_ERR:
            pass
        elif status == PrinterStatus.KLIPPER_ERR:
            pass

    async def onPrinterStatusUpdate(self, data: dict):
        self.state.printerData = data
        asyncio.create_task(self.state.currentPage().onPrinterStatusUpdate(data))

    async def onFileListUpdate(self, data: dict):
        self.state.fileList = data
        asyncio.create_task(self.state.currentPage().onFileListUpdate(data))

    async def changePage(self, page: str):
        if self.state.backstack[-2].name == page:
            self.state.backstack.pop()
        else:
            self.state.backstack.append(self.pages[page](self.state, self.changePage))

        await self.state.display.command("page %s" % page)

    async def init(self):
        await self.state.display.connect()
        await self.state.printer.connect()


if __name__ == "__main__":
    setproctitle("OpenQ1Display")
    loop = asyncio.get_event_loop()
    app = OpenQ1Display()
    asyncio.ensure_future(app.init())
    loop.run_forever()
