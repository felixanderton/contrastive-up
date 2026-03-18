(define (domain logistics)
  (:requirements :strips :typing :action-costs)  ; <-- ADDED :action-costs

  (:types
    city location truck airplane package - object
  )

  (:predicates
    ;; topology
    (in-city ?l - location ?c - city)
    (airport ?l - location)

    ;; vehicles
    (at-truck ?t - truck ?l - location)
    (at-plane ?a - airplane ?l - location)

    ;; packages and cargo
    (at       ?p - package ?l - location)
    (in-truck ?p - package ?t - truck)
    (in-plane ?p - package ?a - airplane)
  )
  
  ;; ADDED A FLUENT TO REPRESENT THE COST OF ACTIONS
  (:functions
    (truck-cost ?t - truck)   ; Cost for truck actions
    (plane-cost ?a - airplane) ; Cost for plane actions
    (total-cost)
  )

  ;; move a truck within a city
  (:action drive-truck
    :parameters (?t - truck ?from - location ?to - location ?c - city)
    :precondition (and
      (at-truck ?t ?from)
      (in-city ?from ?c)
      (in-city ?to   ?c)
      (not (= ?from ?to))
    )
    :effect (and
      (at-truck ?t ?to)
      (not (at-truck ?t ?from))
      (increase (total-cost) (truck-cost ?t)) ; <-- COST EFFECT ADDED
    )
  )

  ;; fly an airplane between airports (across cities)
  (:action fly-plane
    :parameters (?a - airplane ?from - location ?to - location)
    :precondition (and
      (at-plane ?a ?from)
      (airport ?from)
      (airport ?to)
      (not (= ?from ?to))
    )
    :effect (and
      (at-plane ?a ?to)
      (not (at-plane ?a ?from))
      (increase (total-cost) (plane-cost ?a)) ; <-- COST EFFECT ADDED
    )
  )

  ;; load/unload actions remain the same (zero cost)
  ;; ... (load/unload actions as before)
  (:action load-truck
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and
      (at ?p ?l)
      (at-truck ?t ?l)
    )
    :effect (and
      (in-truck ?p ?t)
      (not (at ?p ?l))
    )
  )

  (:action unload-truck
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and
      (in-truck ?p ?t)
      (at-truck ?t ?l)
    )
    :effect (and
      (at ?p ?l)
      (not (in-truck ?p ?t))
    )
  )

  (:action load-plane
    :parameters (?p - package ?a - airplane ?l - location)
    :precondition (and
      (at ?p ?l)
      (at-plane ?a ?l)
      (airport ?l)
    )
    :effect (and
      (in-plane ?p ?a)
      (not (at ?p ?l))
    )
  )

  (:action unload-plane
    :parameters (?p - package ?a - airplane ?l - location)
    :precondition (and
      (in-plane ?p ?a)
      (at-plane ?a ?l)
    )
    :effect (and
      (at ?p ?l)
      (not (in-plane ?p ?a))
    )
  )
)