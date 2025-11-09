
def print_board(board):#Выводит актуальный интерфейс игры
    print('  1 2 3')
    for i in range(3):
        print(f'{i + 1} {' '.join(board[i])}')



def is_valid_move(board, row, col):# проверка хода
    if row < 1 or row > 3 or col < 1 or col > 3:
        return False
    if board[row-1][col-1] == '-':
        return True
    else:
        return False

def check_winner(board):# проверка победителя
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] != '-':#проверка строк, если все элементы одинаковые и они не '-' то
            return board[i][0] # возвращает 0 элемент из той строки в которой получилось равенство

    for i in range(3):
        if board[0][i] == board[1][i] == board[2][i] != '-':#тоже самое что и в цикле выше только уже по столбцам
            return board[0][i]
    if board[0][0] == board[1][1] == board[2][2] != '-':
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != '-':
        return board[0][2]

def is_board_full(board): #проверяет ничью
    for row in board:
        if '-' in row:
            return False
    return True
def main():# основняа функция отвечающая за ввод значений
    board = [['-' for j in range(3)] for i in range(3)]
    current_player = 'X'

    print('Время игры:')
    while True:
        print_board(board)
        print(f'Ход игрока {current_player}')

        try:
            row = int(input('Введите номер строки (1-3): '))
            col = int(input('Введите номер столбца (1-3): '))
        except ValueError:
            print('Пожалуйста, введите числа')
            continue

        if is_valid_move(board, row, col):
            board[row-1][col-1] = current_player

            winner = check_winner(board)
            if winner:
                print_board(board)
                print(f'Игрок {winner} победил!')
                break
            if is_board_full(board):
                print_board(board)
                print('Ничья!')
                break
            current_player = '0' if current_player == 'X' else 'X'
        else:
            print('Неверный ход попробуйте снова.')

if __name__ == '__main__':
    main()