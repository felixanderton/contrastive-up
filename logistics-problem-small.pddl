(define (problem logistics-demo-small)
  (:domain logistics)

  (:objects
    c1 c2          - city
    l1 l2          - location    ; l1: street in c1, l2: street in c2
    a1 a2          - location    ; a1: airport in c1, a2: airport in c2
    t1 t2          - truck
    plane1         - airplane
    p1 p2          - package
  )

  (:init
    ;; topology
    (in-city l1 c1) (in-city a1 c1)
    (in-city l2 c2) (in-city a2 c2)

    (airport a1)
    (airport a2)

    ;; vehicles
    (at-truck t1 l1)
    (at-truck t2 l2)
    (at-plane plane1 a1)

    ;; packages
    ;; p1: from l1 (city 1 street) to l2 (city 2 street)
    (at p1 l1)
    ;; p2: from l2 (city 2 street) to a1 (city 1 airport)
    (at p2 l2)
  )

  (:goal
    (and
      (at p1 l2)
      (at p2 a1)
    )
  )
)
