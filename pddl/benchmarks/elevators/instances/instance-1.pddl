; Small elevator problem: 4 floors, 3 passengers, 1 fast + 1 slow elevator.
(define (problem elevators-time-custom-small)
(:domain elevators-time)
(:objects
  n0 n1 n2 n3  - count
  p0 p1 p2     - passenger
  fast0        - fast-elevator
  slow0-0      - slow-elevator
)
(:init
  (next n0 n1) (next n1 n2) (next n2 n3)
  (above n0 n1) (above n0 n2) (above n0 n3)
  (above n1 n2) (above n1 n3)
  (above n2 n3)
  (lift-at fast0 n0)
  (reachable-floor fast0 n0) (reachable-floor fast0 n1)
  (reachable-floor fast0 n2) (reachable-floor fast0 n3)
  (passengers fast0 n0)
  (can-hold fast0 n1) (can-hold fast0 n2)
  (lift-at slow0-0 n3)
  (reachable-floor slow0-0 n0) (reachable-floor slow0-0 n1)
  (reachable-floor slow0-0 n2) (reachable-floor slow0-0 n3)
  (passengers slow0-0 n0)
  (can-hold slow0-0 n1)
  (passenger-at p0 n0)
  (passenger-at p1 n3)
  (passenger-at p2 n1)
  (= (travel-slow n0 n1) 10) (= (travel-slow n0 n2) 18) (= (travel-slow n0 n3) 26)
  (= (travel-slow n1 n2) 10) (= (travel-slow n1 n3) 18) (= (travel-slow n2 n3) 10)
  (= (travel-fast n0 n1) 6) (= (travel-fast n0 n2) 10) (= (travel-fast n0 n3) 14)
  (= (travel-fast n1 n2) 6) (= (travel-fast n1 n3) 10) (= (travel-fast n2 n3) 6)
)
(:goal (and
  (passenger-at p0 n3)
  (passenger-at p1 n0)
  (passenger-at p2 n2)
))
(:metric minimize (total-time))
)
