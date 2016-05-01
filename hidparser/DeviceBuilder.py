import copy as _copy
from hidparser.enums import CollectionType, ReportFlags, EnumMask, ReportType
from hidparser.UsagePage import UsagePage, Usage, UsageType, UsageRange
from hidparser.Device import Device, Report, ReportGroup, Collection
from hidparser.helper import ValueRange

from typing import Union as _Union


class DeviceBuilder:
    def __init__(self):
        self._state_stack = []
        self._report_id = 0
        self._usage_page = None
        self._usages = []

        self.report_size = 0
        self.report_count = 0
        self.logical_range = ValueRange()
        self.physical_range = self.logical_range

        self._collection = Collection(allowed_usage_types=UsageType.COLLECTION_APPLICATION)
        self._current_collection = self._collection

    def add_report(self, report_type: ReportType, flags: _Union[ReportFlags, EnumMask, int]):
        usages = []
        try:
            while len(usages) < self.report_count:
                usage = self._usages.pop(0) if len(self._usages) > 1 else self._usages[0]
                usages.extend(usage.get_range() if isinstance(usage, UsageRange) else [usage])
        except IndexError:
            if not flags & ReportFlags.CONSTANT:
                raise

        self._current_collection.append(Report(
            report_id=self._report_id,
            report_type=report_type,
            usages=usages,
            size=self.report_size,
            count=self.report_count,
            logical_range=_copy.copy(self.logical_range),
            physical_range=_copy.copy(self.physical_range),
            flags=flags
        ))

    def set_report_id(self, report_id: int):
        self._report_id = report_id

    def set_usage_range(self, minimum=None, maximum=None):
        usage = self._usages[len(self._usages)-1] if len(self._usages) else None
        if usage is None or not isinstance(usage, UsageRange):
            usage = UsageRange(self._usage_page)
            self._usages.append(usage)

        if minimum is not None:
            usage.minimum = minimum
        if maximum is not None:
            usage.maximum = maximum

    def set_logical_range(self, minimum = None, maximum = None):
        if minimum is not None:
            self.logical_range.minimum = minimum

        if maximum is not None:
            self.logical_range.maximum = maximum

    def set_physical_range(self, minimum=None, maximum=None):
        if minimum is not None:
            self.physical_range.minimum = minimum

        if maximum is not None:
            self.physical_range.maximum = maximum

    def add_usage(self, usage: _Union[UsagePage, Usage, int]):
        if isinstance(usage, Usage):
            self._usages.append(usage)
        elif isinstance(usage, UsagePage):
            self._usages.append(usage.value)
        else:
            usage_page = self._usage_page if (usage & ~0xFFFF) == 0 else UsagePage.find_usage_page((usage & ~0xFFFF) >> 16)
            self._usages.append(usage_page.get_usage(usage & 0xFFFF))

    def set_usage_page(self, usage_page: UsagePage.__class__):
        self._usage_page = usage_page
        self._usages.clear()

    def push_collection(self, collection: CollectionType):
        try:
            usage = self._usages.pop(0)
        except IndexError:
            usage = None
        collection_element = Collection(
            usage=usage,
            parent=self._current_collection,
            collection_type=collection
        )
        self._current_collection.append(collection_element)
        self._current_collection = collection_element

        self._usages.clear()
        return self

    def pop_collection(self):
        if self._current_collection.parent is None:
            raise RuntimeError("Can not pop collection state")
        self._current_collection = self._current_collection.parent

        self._usages.clear()
        return self

    def push(self):
        state = _copy.deepcopy(self.__dict__)
        if "_state_stack" in state.keys():
            del state["_state_stack"]
        self._state_stack.append(state)
        return self

    def pop(self):
        if len(self._state_stack) > 0:
            state = self._state_stack.pop()
            self.__dict__.update(state)
        return self

    def build(self):
        return Device(self._collection.items)