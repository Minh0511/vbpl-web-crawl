class VbplFullTextField:
    def __init__(self):
        self.current_big_part_number = None
        self.current_big_part_name = None
        self.current_chapter_number = None
        self.current_chapter_name = None
        self.current_part_number = None
        self.current_part_name = None
        self.current_mini_part_number = None
        self.current_mini_part_name = None

    def reset_part(self):
        self.current_part_number = None
        self.current_part_name = None
        self.current_mini_part_number = None
        self.current_mini_part_name = None

    def __str__(self):
        return (f'Phần thứ {self.current_big_part_number} {self.current_big_part_name}, '
                f'chương {self.current_chapter_number} {self.current_chapter_name}, '
                f'mục {self.current_part_number} {self.current_part_name}, '
                f'tiểu mục {self.current_mini_part_number} {self.current_mini_part_name}')
