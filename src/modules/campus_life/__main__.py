import clubs
import handbook


def main():
    print("📥 Starting parsing modules...\n")

    handbook.parse()
    clubs.parse()

    print("\n✅ All modules parsed.")


if __name__ == "__main__":
    main()
