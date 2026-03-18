(define (problem logistics-demo-medium)
  (:domain logistics)

  (:objects
    ;; cities
    c1 c2 c3                 - city

    ;; locations: two streets + one airport per city
    l1 l2 a1                 - location   ; city 1
    l3 l4 a2                 - location   ; city 2
    l5 l6 a3                 - location   ; city 3

    ;; vehicles
    t1 t2 t3                 - truck
    plane1 plane2            - airplane

    ;; packages
    p1 p2 p3 p4 p5        - package
  )

  (:init
    ;; topology: where locations belong
    (in-city l1 c1) (in-city l2 c1) (in-city a1 c1)
    (in-city l3 c2) (in-city l4 c2) (in-city a2 c2)
    (in-city l5 c3) (in-city l6 c3) (in-city a3 c3)

    ;; airports
    (airport a1)
    (airport a2)
    (airport a3)

    ;; trucks
    (at-truck t1 l1)   ; city 1 street
    (at-truck t2 l3)   ; city 2 street
    (at-truck t3 l5)   ; city 3 street

    ;; planes
    (at-plane plane1 a1)
    (at-plane plane2 a2)

    ;; packages:
    ;; p1: c1 street -> c3 street
    (at p1 l1)
    ;; p2: c1 street -> c2 street
    (at p2 l2)
    ;; p3: c2 street -> c1 street
    (at p3 l3)
    ;; p4: c3 street -> c2 airport
    (at p4 l5)
    ;; p5: c3 street -> c1 airport
    (at p5 l6)

    (= (truck-cost t1) 1)    ; Cost 1 for t1
    (= (truck-cost t2) 2)    ; Cost 2 for t2 (maybe it's a gas-guzzler!)
    (= (plane-cost plane1) 10)   ; Cost 10 for plane1
    (= (plane-cost plane2) 8)    ; Cost 8 for plane2
    (= (total-cost) 0)
  )

  (:goal
    (and
      ;; p1 from l1 (c1) to l5 (c3)
      (at p1 l5)
      ;; p2 from l2 (c1) to l4 (c2)
      (at p2 l4)
      ;; p3 from l3 (c2) to l1 (c1)
      (at p3 l1)
      ;; p4 from l5 (c3) to a2 (c2 airport)
      (at p4 a2)
      ;; p5 from l6 (c3) to a1 (c1 airport)
      (at p5 a1)
    )
  )
  (:metric minimize (total-cost))
)
