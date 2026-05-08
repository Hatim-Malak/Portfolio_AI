def individual_serial(project) -> dict:
    return {
        "id":str(project["_id"]),
        "title":project["title"],
        "readme":project["readme"],
        "description":project["description"],
        "languages":project["languages"],
        "mobile_url":project["mobile_url"],
        "desktop_url":project["desktop_url"],
        "updated_at":project["updated_at"],
        "github_link":project["github_link"],
        "live_link":project["live_link"]
    }

def list_serial(projects) -> list:
    return [individual_serial(project) for project in projects]