# 스마트야드 ROS 2 멀티 PC 실습

Windows 11 + WSL2 mirrored + Ubuntu 22.04 + ROS 2 Humble + Python 기반 교육 자료입니다.

**수업 교재: [docs/index.html](docs/index.html)** — 로컬 브라우저에서 열면 됩니다. 설치, 이론, 패키지 생성, 빌드, 네트워크, 기능별 실습, 오류 복구, GitHub 업로드, 전체 소스를 포함합니다.

## 검증 상태

- Python 3.10 문법 호환 정적 검사, 패키지 XML 및 ROS 독립 로직 16개 검사 통과.
- 제작 환경에서 WSL 접근이 제한되어 ROS/colcon 실기동과 4대 PC 통신은 미검증.
- 실제 Ubuntu에서 `scripts/ros_integration_check.py`, 수업실에서 HTML 12장의 체크리스트를 실행하세요.
- 수치와 동작은 교육용 모형이며 실제 운반 장비의 안전 제어를 구현한 제품이 아닙니다.

## 빠른 시작

ZIP을 Ubuntu 홈에 풀면 `~/smartyard_ws`가 됩니다. ROS가 없다면 교재 2장에 따라 설치합니다.

```bash
cd ~/smartyard_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src --rosdistro humble -r -y
colcon build --symlink-install
source scripts/env.sh 31
ros2 launch smartyard_lab all.launch.py
```

새 터미널:

```bash
cd ~/smartyard_ws
source scripts/env.sh 31
ros2 param set /yard01/control_center job_id JOB_001
ros2 service call /yard01/start_job std_srvs/srv/Trigger "{}"
# 운반 중 취소하려면
ros2 service call /yard01/cancel_job std_srvs/srv/Trigger "{}"
```

`REQUEST_QUEUED`는 접수이며 완료가 아닙니다. 관제의 최종 `RESULT`를 확인합니다.

## 네 PC 실행

`all.launch.py`를 종료한 후 모든 PC에서 동일 커밋을 빌드하고 새 터미널에 `source scripts/env.sh 31`을 실행합니다.

|PC|명령|역할|
|---|---|---|
|1|`ros2 launch smartyard_lab pc1.launch.py`|센서|
|2|`ros2 launch smartyard_lab pc2.launch.py`|관제|
|3|`ros2 launch smartyard_lab pc3.launch.py`|판단 서비스|
|4|`ros2 launch smartyard_lab pc4.launch.py`|운반 액션|

서로 다른 PC의 통신에는 같은 도메인뿐 아니라 mirrored 네트워크, 호환 QoS, 방화벽과 LAN 경로가 필요합니다.

## 원격 파라미터

```bash
ros2 param set /yard01/transporter travel_speed_mps 0.5
ros2 run smartyard_lab parameter_tool get /yard01/transporter travel_speed_mps
ros2 run smartyard_lab parameter_tool set /yard01/sensor_station wind_speed_mps 12.0
```

기본 센서 QoS는 Best Effort입니다. 관찰 명령은 다음처럼 실행합니다.

```bash
ros2 topic echo /yard01/sensor_state --qos-reliability best_effort
```

## 테스트

```bash
python3 scripts/validate_local.py
colcon test --packages-select smartyard_lab
colcon test-result --verbose
python3 scripts/ros_integration_check.py
```

통합 스크립트는 별도 도메인 91 / localhost 전용으로 네 로컬 프로세스를 실행합니다. 다중 PC 검증을 대신하지 않습니다.

## 중요한 모델 정책

- 하나의 운반 작업만 수락합니다. 수락한 job_id는 서버 프로세스 안에서 재사용하지 않습니다.
- 매 실험은 독립적인 A→B 이동입니다. 재고·실제 블록 위치·반납·예약 DB는 구현하지 않습니다.
- 판단 서버와 운반 서버의 한도는 별도의 설정입니다. PC 4는 실행 중에도 센서 조건을 검사합니다.
- PC 2가 사라졌다고 PC 4가 자동 취소되지는 않습니다. 센서 stale 중단은 별도로 구현되어 있습니다.
- runtime 설정은 자동 저장하지 않습니다. `ros2 param dump`와 launch config로 복원합니다.
- GitHub 최초 생성·업로드 절차는 교재 11장에 있습니다. 인증 정보와 빌드 결과는 커밋하지 않습니다.

License: MIT. 기본 maintainer 메타데이터는 수업 배포자 정보로 수정할 수 있습니다.
