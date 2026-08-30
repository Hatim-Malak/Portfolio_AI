def individual_serial(project) -> dict:
    return {
        "id":str(project["_id"]),
        "title":project.get("title", ""),
        "readme":project.get("readme", ""),
        "description":project.get("description", ""),
        "languages":project.get("languages", {}),
        "mobile_url":project.get("mobile_url", ""),
        "desktop_url":project.get("desktop_url", ""),
        "updated_at":project.get("updated_at", ""),
        "github_link":project.get("github_link", ""),
        "live_link":project.get("live_link", ""),
        "video": project.get("video"),
        "gallery": project.get("gallery", [])
    }

def list_serial(projects) -> list:
    return [individual_serial(project) for project in projects]

def individual_user_serial(user):
    return {
        "id":str(user["_id"]),
        "email":user["email"],
        "passwordHash":user["passwordHash"],
    }

def list_user_serial(users):
    return [individual_user_serial(user) for user in users]