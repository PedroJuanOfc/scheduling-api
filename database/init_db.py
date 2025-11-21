from database.database import engine, SessionLocal
from database.models import Base, Especialidade

def init_database():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        especialidades_existentes = db.query(Especialidade).count()
        
        if especialidades_existentes == 0:
            especialidades_padrao = [
                Especialidade(
                    nome="Clínica Geral",
                    descricao="Consultas de rotina e check-ups",
                    icone="🩺"
                ),
                Especialidade(
                    nome="Odontologia",
                    descricao="Cuidados dentários e saúde bucal",
                    icone="🦷"
                ),
                Especialidade(
                    nome="Oftalmologia",
                    descricao="Exames de vista e saúde ocular",
                    icone="👁️"
                ),
                Especialidade(
                    nome="Cardiologia",
                    descricao="Saúde do coração e sistema cardiovascular",
                    icone="❤️"
                )
            ]
            
            for especialidade in especialidades_padrao:
                db.add(especialidade)
            
            db.commit()
    
    except Exception as e:
        db.rollback()
        print(f"Erro ao inicializar banco de dados: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    init_database()