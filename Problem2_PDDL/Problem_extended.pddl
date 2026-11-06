(define (problem mars-rover-extended)
 (:domain mars-rover)
 (:objects Curiosity - rover Drill1 - drill Bay1 Bay2 - bay
           Base SiteA SiteB SiteC SiteD SiteE SiteF - location
           Rock1 Rock2 Rock3 Rock4 Rock5 Rock6 Rock7 - rock)
 (:init (at Curiosity Base) (drill-at Drill1 SiteE) (bay-empty Bay1) (bay-empty Bay2) (connected Base SiteA) (connected SiteA SiteC) (connected SiteB SiteD) (connected SiteC SiteE) (connected SiteD SiteE) (connected SiteE SiteF) (connected SiteA Base) (connected SiteC SiteA) (connected SiteD SiteB) (connected SiteE SiteC) (connected SiteE SiteD) (connected SiteF SiteE) (connected SiteC SiteD) (rock-at Rock1 SiteA) (rock-at Rock2 SiteB) (rock-at Rock3 SiteC) (rock-at Rock4 SiteD) (rock-at Rock5 SiteF) (rock-at Rock6 SiteE) (rock-at Rock7 SiteF) (soft Rock1) (soft Rock2) (hard Rock3) (soft Rock4) (hard Rock5) (soft Rock6) (hard Rock7))
 (:goal (and (at Curiosity Base) (bay-empty Bay1) (bay-empty Bay2) (rock-at Rock1 Base) (rock-at Rock2 Base) (rock-at Rock3 Base) (rock-at Rock4 Base) (rock-at Rock5 Base) (rock-at Rock6 Base) (rock-at Rock7 Base)))
)
