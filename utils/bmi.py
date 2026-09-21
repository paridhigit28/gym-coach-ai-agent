def calculate_bmi(weight_kg: float, height_m: float) -> float:
    if not weight_kg or not height_m or height_m <= 0:
        return 0.0
    return round(weight_kg / (height_m ** 2), 1)

def get_bmi_category(bmi: float) -> str:
    if bmi == 0.0:
        return "Unknown"
    elif bmi < 18.5:
        return "Underweight"
    elif 18.5 <= bmi < 24.9:
        return "Normal Weight"
    elif 25.0 <= bmi < 29.9:
        return "Overweight"
    else:
        return "Obese"
