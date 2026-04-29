import argparse
import secrets
import string

from werkzeug.security import generate_password_hash


DEFAULT_LENGTH = 16
ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"


def generate_password(length):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def main():
    parser = argparse.ArgumentParser(
        description="Generate a plain password and Werkzeug hash for the users table."
    )
    parser.add_argument(
        "--password",
        help="Use an existing plain password instead of generating one.",
    )
    parser.add_argument(
        "--length",
        type=int,
        default=DEFAULT_LENGTH,
        help=f"Generated password length. Default: {DEFAULT_LENGTH}.",
    )
    args = parser.parse_args()

    if args.length < 8:
        raise SystemExit("Password length must be at least 8 characters.")

    password = args.password or generate_password(args.length)
    password_hash = generate_password_hash(password)

    print("Plain password:")
    print(password)
    print()
    print("Database password_hash:")
    print(password_hash)
    print()
    print("SQL value:")
    print(f"'{password_hash}'")


if __name__ == "__main__":
    main()
