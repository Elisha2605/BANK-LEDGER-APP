from typing import TypeVar, Generic

T = TypeVar("T")


class Result(Generic[T]):
    def is_err(self) -> bool:
        return True if type(self) == Err else False

    def is_ok(self) -> bool:
        return True if type(self) == Ok else False

    def data(self) -> T:
        if self.is_ok():
            return self.ok  # type: ignore
        else:
            raise Exception(f"Attempted to open an Ok, but opened an Err: '{self.detail}'") #type: ignore | can only be an Err if we get here

    def err(self) -> T:
        if self.is_err():
            return self.detail  # type: ignore
        else:
            raise Exception("Attempted to open an Err but opened an Ok: '{self.ok}'")

    def to_bool(self):
        if type(self) == Ok:
            return True
        else:
            return False

    def to_list(self):
        if type(self) == Ok:
            return_list = []
            # If the data stored is Iterable, iterate it and append to array
            if hasattr(self.ok, '__iter__'): # type: ignore
                for data in self.ok:  # type: ignore
                    return_list.append(data)
            # If it not, then append the whole of it in an array
            else:
                return_list.append(self.ok) # type: ignore

            return return_list
        else:
            return list()


    def __str__(self) -> str:
        return str(self.__dict__)
    


class Err(Result, Generic[T]):
    error: str
    detail: T

    def __init__(self, kind: str, detail: T) -> None:
        self.error = kind
        self.detail: T = detail


class Ok(Result, Generic[T]):
    ok: T

    def __init__(self, data: T) -> None:
        self.ok: T = data
