"""Preflight all synthetic input variants through the production parser."""

from loadtest.run import samples, validate_samples

if __name__ == "__main__":
    inputs = samples()
    extracted = validate_samples(inputs)
    for name, (text, data, _) in inputs.items():
        print(name, len(text) + extracted[name], len(data or b""))
