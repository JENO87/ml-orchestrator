

class MockClass:
    def __init__(self, mock_variable: str = "This is a mockup class") -> None:
        self.mock_variable = mock_variable

    def rename_mock_var(self):
        self.mock_variable = "This is now a mockup variable"
