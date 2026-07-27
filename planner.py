def calculate_priority(subject):
    return subject["difficulty"] / subject["days_left"]

def generate_plan(subjects, hours_per_day):

    subjects = subjects.copy()
    weekly_plan = []

    for day in range(1, 8):

        subjects.sort(key=calculate_priority, reverse=True)

        total_priority = sum(calculate_priority(s) for s in subjects)

        daily = []

        for s in subjects:
            hours = (calculate_priority(s) / total_priority) * hours_per_day

            daily.append({
                "name": s["name"],
                "hours": round(hours, 1)
            })

        weekly_plan.append({
            "day": day,
            "plan": daily
        })

        for s in subjects:
            if s["days_left"] > 1:
                s["days_left"] -= 1

    return weekly_plan