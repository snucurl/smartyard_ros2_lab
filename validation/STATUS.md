# 검증 범위

2026-11-16 제작 환경: Windows, WSL 호출은 E_ACCESSDENIED.

실행한 검사는 `local_checks.json` 및 `html_checks.json`을 참고하세요.
ROS 독립 로직을 검사했으며, rclpy를 모방해 통신 성공을 주장하지 않습니다.

다음 항목은 실제 Ubuntu 22.04 / Humble 및 실습 LAN에서 확인해야 합니다.

- rosdep 및 colcon 빌드, rosidl 인터페이스 생성
- rclpy 실기동, 서비스/액션/파라미터 통합 스크립트
- WSL mirrored, 방화벽, 멀티캐스트, 네 PC 간 전달

교재 12장 체크리스트와 `scripts/ros_integration_check.py`를 사용하세요.
