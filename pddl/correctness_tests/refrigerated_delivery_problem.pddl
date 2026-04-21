(define (problem refrigerated_delivery)
	(:domain refrigerated_delivery)
	(:objects
		t1 t2 - truck
		d1 - driver
		m - meat
		ce - cereal
		a b c - location
	)
	(:init
		(at t1 a)
		(at t2 a)
		(at d1 a)

		(at m a)
		(at ce a)

		(refrigerated t2)

		(= (time_to_drive a b) 20)
		(= (time_to_drive b a) 20)
		(= (time_to_drive b c) 15)
		(= (time_to_drive c b) 15)
		(= (time_to_drive a c) 10)
		(= (time_to_drive c a) 10)
		
		(can_deliver m)
		(can_deliver ce)

		(at 22 (not (can_deliver m)))
		(at 1000 (not (can_deliver ce)))

	)
	(:goal (and
		(at m b)
		(at ce c)
	))

(:metric minimize (total-time))

)
