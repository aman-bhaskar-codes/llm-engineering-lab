import json


def aggregate_results(results: list):

    merged = {}

    for res in results:
        try:
            json_start = res.find("{")
            json_end = res.rfind("}") + 1

            parsed = json.loads(res[json_start:json_end])

            for key, value in parsed.items():

                if key not in merged:
                    merged[key] = value

                else:
                    if isinstance(value, list):
                        merged[key] = list(set(merged[key] + value))

                    else:
                        merged[key] = value

        except:
            continue

    return merged