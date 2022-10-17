import re
import sys
from recipe_scrapers import scrape_me, WebsiteNotImplementedError
from parse_ingredients import parse_ingredient

# List of single stop words used to remove from ingredient list. Prevents outputs like @onion @powder{1%tbsp}{1%tbsp}
single_stop_words = {
    "and",
    "or",
    "for",
    "the",
    "of",
    "powder",
    "syrup",
    "pinch",
    "cheese",
    "ground",
    "powdered",
    "seeds",
}

# List of small amount types to convert quantity from 0 to 1.
small_amount_words = {"dash", "pinch", "sprinkle", "smidgen", "drop", "bunch"}


def eprint(*args, **kwargs):
    """
    Print to standard error for the console.
    """
    print(*args, file=sys.stderr, **kwargs)


# Rip from https://www.geeksforgeeks.org/python-print-sublists-list/
def sub_lists(l):
    """
    Create sublists of an entire list
    """
    lists = [[]]
    for i in range(len(l) + 1):
        for j in range(i):
            lists.append(l[j:i])
    return lists


def highlight_replacement_in_text(instructions, match_start, match_end):
    start = match_start - 18
    end = match_end + 18

    if start < 0:
        start = 0

    if end > len(instructions):
        end = len(instructions)

    eprint("...", instructions[start:end], "...")
    eprint(" " * (3 + match_start - start), "^" * (match_end - match_start))


def print_recipe(title, link, total_time, image, instructions, to_file=False):
    """
    Write the recipe to a file
    args:
    @param title the title of the recipe
    @param link the link to the recipe
    @param total_time the total amount of time for the recipe
    @param image the image associated with the recipe
    @param instructions the instructions for the desired recipe
    @param to_file write formatted recipe to file instead to stdout
    """
    recipe = [
        f">> source: {link}",
        f">> time required: {total_time} minutes",
        f">> image: {image}",
        "\n" + instructions,
    ]
    if to_file:
        with open(f"{title}.cook", "w") as outfile:
            outfile.write("\n".join(recipe) + "\n")
    else:
        print("\n".join(recipe))


def run(args_link, args_file):
    # give the url as a string, it can be url from any site listed below
    try:
        scraper = scrape_me(args_link)
    except WebsiteNotImplementedError as e:
        print(
            "The domain is currently not supported, %s. You can request adding this domain at https://github.com/hhursev/recipe-scrapers."
            % e.domain
        )
        sys.exit(1)

    # Q: What if the recipe site I want to extract information from is not listed below?
    # A: You can give it a try with the wild_mode option! If there is Schema/Recipe available it will work just fine.
    # scraper = scrape_me('https://www.feastingathome.com/tomato-risotto/', wild_mode=True)

    title = scraper.title()
    image = scraper.image()
    total_time = scraper.total_time()

    eprint("Title:", title)
    eprint("Image:", image)

    instructions = scraper.instructions()
    # Remove those pesky punctuation
    ingredients_list = [
        parse_ingredient(re.sub(r"\.", "", ingredient))
        for ingredient in scraper.ingredients()
    ]

    # Convert the timers
    time_regex_match_str = (
        r"(\d+|\d+\.\d+|\d+-\d+|\d+ to \d+) (min(?:utes)?|hours?|days?)"
    )
    instructions = re.sub(time_regex_match_str, r"~{\1%\2}", instructions)

    for combined_ingredient in ingredients_list:

        quantity = combined_ingredient.quantity
        unit = combined_ingredient.unit

        # Remove decimal places of whole numbers, such as 1.0 to 1
        if quantity % 1 == 0:
            quantity = int(quantity)

        # Truncate repeating decimals such as .333333
        if len(str(quantity)) > 5:
            quantity = f"{quantity:.2f}"

        # Unit is a small amount word and quantity is 0
        if (unit in small_amount_words) and (quantity == 0):
            quantity = 1

        # remove extra characters aka ')'
        ingredient_fixed = re.sub(r" ?\)", "", combined_ingredient.name)

        # Create sublists for word matches
        # Idea is to greedly match as many words as possible
        ing_list = sub_lists(ingredient_fixed.split(" "))

        # Filter out empty sublist
        ing_list = list(filter(lambda x: len(x) > 0, ing_list))

        # Remove single stop words
        if len(ing_list) > 1:
            ing_list = list(filter(lambda x: x[0] not in single_stop_words, ing_list))

        # Now generate regex string to  match
        ing_list = sorted(ing_list, reverse=True, key=lambda x: len(x))
        ing_regex_match_str = "|".join(
            list(map(lambda x: rf'\b{" ".join(x)}\b', ing_list))
        )
        ing_regex_match_str = "(?:[^@])(" + ing_regex_match_str + ")"
        # regex match the text
        match_obj = re.search(ing_regex_match_str, instructions, flags=re.I)

        eprint("")
        eprint(
            "✅" if match_obj is not None else "❌",
            f"@{combined_ingredient.name}{{{quantity}%{unit}}}"
            if unit != ""
            else (
                f"@{combined_ingredient.name}{{}}"
                if quantity == 0
                else f"@{combined_ingredient.name}{{{quantity}}}"
            ),
        )

        # If no match skip ingredient
        if match_obj is None:
            continue

        match_start = match_obj.start(1)
        match_end = match_obj.end(1)

        highlight_replacement_in_text(instructions, match_start, match_end)
        ing_replacement = (
            f"@{match_obj[1]}{{{quantity}%{unit}}}"
            if unit != ""
            else (
                f"@{match_obj[1]}{{}}"
                if quantity == 0
                else f"@{match_obj[1]}{{{quantity}}}"
            )
        )
        instructions = (
            instructions[0:match_start]
            + ing_replacement
            + instructions[match_obj.end() :]
        )

    instructions = instructions.replace("\n", "\n\n")

    print_recipe(title, args_link, total_time, image, instructions, to_file=args_file)
