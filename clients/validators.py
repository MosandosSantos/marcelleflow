import re


def normalize_digits(value):
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits or None


def is_valid_cpf(value):
    cpf = normalize_digits(value)
    if not cpf or len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False

    def calc_digit(base, weights):
        total = sum(int(d) * w for d, w in zip(base, weights))
        remainder = total % 11
        return '0' if remainder < 2 else str(11 - remainder)

    d1 = calc_digit(cpf[:9], range(10, 1, -1))
    d2 = calc_digit(cpf[:9] + d1, range(11, 1, -1))
    return cpf[-2:] == d1 + d2


def is_valid_cnpj(value):
    cnpj = normalize_digits(value)
    if not cnpj or len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False

    def calc_digit(base, weights):
        total = sum(int(d) * w for d, w in zip(base, weights))
        remainder = total % 11
        return '0' if remainder < 2 else str(11 - remainder)

    weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_second = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    d1 = calc_digit(cnpj[:12], weights_first)
    d2 = calc_digit(cnpj[:12] + d1, weights_second)
    return cnpj[-2:] == d1 + d2
