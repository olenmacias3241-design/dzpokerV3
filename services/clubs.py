# dzpokerV3/services/clubs.py
from database import Club, ClubMember, SessionLocal, User

def create_club(db, name, owner_id, description=None):
    """创建俱乐部"""
    club = Club(name=name, owner_id=owner_id, description=description)
    db.add(club)
    db.commit()
    db.refresh(club)
    
    # 自动添加创建者为成员
    member = ClubMember(club_id=club.id, user_id=owner_id, role='owner')
    db.add(member)
    db.commit()
    
    return club

def list_clubs(db):
    """列出所有俱乐部"""
    return db.query(Club).all()

def get_club(db, club_id):
    """获取俱乐部详情"""
    return db.query(Club).filter(Club.id == club_id).first()

def join_club(db, club_id, user_id):
    """加入俱乐部"""
    existing = db.query(ClubMember).filter_by(club_id=club_id, user_id=user_id).first()
    if existing:
        return None, "已经是俱乐部成员"
    
    member = ClubMember(club_id=club_id, user_id=user_id, role='member')
    db.add(member)
    db.commit()
    return member, None

def get_club_members(db, club_id):
    """获取俱乐部成员列表"""
    return db.query(ClubMember).filter(ClubMember.club_id == club_id).all()


def remove_member(db, club_id, user_id, operator_id):
    """移除俱乐部成员（需要管理员权限）"""
    # 检查操作者权限
    operator = db.query(ClubMember).filter_by(club_id=club_id, user_id=operator_id).first()
    if not operator or operator.role not in ('owner', 'admin'):
        return False, "权限不足"
    
    # 不能移除所有者
    target = db.query(ClubMember).filter_by(club_id=club_id, user_id=user_id).first()
    if not target:
        return False, "成员不存在"
    if target.role == 'owner':
        return False, "不能移除所有者"
    
    db.delete(target)
    db.commit()
    return True, None


def set_member_role(db, club_id, user_id, new_role, operator_id):
    """设置成员角色（需要所有者权限）"""
    operator = db.query(ClubMember).filter_by(club_id=club_id, user_id=operator_id).first()
    if not operator or operator.role != 'owner':
        return False, "只有所有者可以设置角色"
    
    member = db.query(ClubMember).filter_by(club_id=club_id, user_id=user_id).first()
    if not member:
        return False, "成员不存在"
    
    if new_role not in ('member', 'admin'):
        return False, "无效的角色"
    
    member.role = new_role
    db.commit()
    return True, None


def leave_club(db, club_id, user_id):
    """离开俱乐部（所有者不可离开）。"""
    member = db.query(ClubMember).filter_by(club_id=club_id, user_id=user_id).first()
    if not member:
        return False, "不是俱乐部成员"
    if member.role == "owner":
        return False, "所有者不能离开俱乐部"
    db.delete(member)
    db.commit()
    return True, None


def get_club_members_with_names(db, club_id):
    """获取成员列表，附带用户名。"""
    rows = db.query(ClubMember, User).join(
        User, User.id == ClubMember.user_id
    ).filter(ClubMember.club_id == club_id).all()
    return [
        {"user_id": m.user_id, "username": u.username or f"用户{m.user_id}", "role": m.role}
        for m, u in rows
    ]


def update_club_info(db, club_id, operator_id, name=None, description=None):
    """更新俱乐部信息（需要管理员权限）"""
    operator = db.query(ClubMember).filter_by(club_id=club_id, user_id=operator_id).first()
    if not operator or operator.role not in ('owner', 'admin'):
        return False, "权限不足"
    
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        return False, "俱乐部不存在"
    
    if name:
        club.name = name
    if description is not None:
        club.description = description
    
    db.commit()
    return True, None

