from app.database import SessionLocal
from app.models import HCP


def seed_hcps() -> None:
    session = SessionLocal()
    try:
        if session.query(HCP).count() > 0:
            print("Seed skipped: HCP records already exist.")
            return

        hcps = [
            HCP(
                name="Dr. Ananya Mehta",
                specialty="Cardiologist",
                hospital="Kokilaben Dhirubhai Ambani Hospital",
                city="Mumbai",
                tier="tier1",
                email="ananya.mehta@kokilabenhospital.com",
                phone="+91-9820011122",
            ),
            HCP(
                name="Dr. Rohan Kulkarni",
                specialty="Endocrinologist",
                hospital="Apollo Spectra",
                city="Mumbai",
                tier="tier2",
                email="rohan.kulkarni@apollospectra.com",
                phone="+91-9820022233",
            ),
            HCP(
                name="Dr. Priyanka Shah",
                specialty="Oncologist",
                hospital="Tata Memorial Hospital",
                city="Mumbai",
                tier="tier1",
                email="priyanka.shah@tmc.gov.in",
                phone="+91-9820033344",
            ),
            HCP(
                name="Dr. Arjun Bhatia",
                specialty="Cardiologist",
                hospital="Max Super Speciality Hospital",
                city="Delhi",
                tier="tier1",
                email="arjun.bhatia@maxhealthcare.com",
                phone="+91-9810011155",
            ),
            HCP(
                name="Dr. Nivedita Rao",
                specialty="Endocrinologist",
                hospital="Fortis Escorts",
                city="Delhi",
                tier="tier2",
                email="nivedita.rao@fortishealthcare.com",
                phone="+91-9810022266",
            ),
            HCP(
                name="Dr. Karan Malhotra",
                specialty="Oncologist",
                hospital="Rajiv Gandhi Cancer Institute",
                city="Delhi",
                tier="tier2",
                email="karan.malhotra@rgcirc.org",
                phone="+91-9810033377",
            ),
            HCP(
                name="Dr. Sneha Iyer",
                specialty="Cardiologist",
                hospital="Narayana Health City",
                city="Bengaluru",
                tier="tier1",
                email="sneha.iyer@narayanahealth.org",
                phone="+91-9886011188",
            ),
            HCP(
                name="Dr. Vishal Reddy",
                specialty="Oncologist",
                hospital="Manipal Hospitals",
                city="Bengaluru",
                tier="tier2",
                email="vishal.reddy@manipalhospitals.com",
                phone="+91-9886022299",
            ),
        ]

        session.add_all(hcps)
        session.commit()
        print("Seed complete: inserted 8 HCP records.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_hcps()
