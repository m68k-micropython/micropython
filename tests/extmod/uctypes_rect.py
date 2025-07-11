try:
    Rect
except NameError:
    print("SKIP")
    raise SystemExit

r = Rect()
print(f"{repr(r)[:13]!r}")
print(r.top, r.left, r.bottom, r.right)
r = Rect(1, 2, 3, 4)
print(r.top, r.left, r.bottom, r.right)
r = Rect(1, 2, right=4)
print(r.top, r.left, r.bottom, r.right)
