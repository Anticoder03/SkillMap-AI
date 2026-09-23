"""Global template context processors."""


def active_page(request):
    """Expose the active navigation section based on the current URL path."""
    path = request.path or ""
    resolved = ""
    for section, marker in [
        ("dashboard", "/dashboard/"),
        ("careers", "/careers/"),
        ("assessment", "/assessment/"),
        ("roadmap", "/roadmap/"),
        ("recommendations", "/recommendations/"),
    ]:
        if path.startswith(marker):
            resolved = section
            break
    if path in ("", "/"):
        resolved = "home"
    return {"active_page": resolved, "request_path": path}