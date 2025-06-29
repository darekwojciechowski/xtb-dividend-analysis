# plot_style.py


def apply_github_dark_theme():
    """
    Apply a GitHub Dark-inspired theme to matplotlib and seaborn plots.
    """
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "axes.facecolor": "#0D1117",  # Dark background
            "figure.facecolor": "#0D1117",  # Dark figure background
            "text.color": "#ABB2BF",  # Light gray text
            "axes.labelcolor": "#61AFEF",  # Blue labels
            "xtick.color": "#ABB2BF",  # Light gray ticks
            "ytick.color": "#ABB2BF",  # Light gray ticks
            "font.family": "monospace",  # Monospace font for consistency
            "font.size": 10,
            "axes.titlesize": 10,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )


github_palette = [
    "#E06C75",  # Soft Red
    "#61AFEF",  # Light Blue
    "#98C379",  # Green
    "#C678DD",  # Purple
    "#E5C07B",  # Gold
    "#56B6C2",  # Cyan
    "#D19A66",  # Orange
    "#BE5046",  # Dark Red
    "#7F848E",  # Gray
    "#528BFF",  # Bright Blue
    "#FFA07A",  # Salmon
    "#B22222",  # Firebrick
    "#2E8B57",  # Sea Green
    "#DAA520",  # Goldenrod
    "#8A2BE2",  # Blue Violet
    "#FF6347",  # Tomato
    "#4682B4",  # Steel Blue
    "#FF69B4",  # Hot Pink
    "#32CD32",  # Lime Green
    "#FFD700",  # Bright Gold
]
