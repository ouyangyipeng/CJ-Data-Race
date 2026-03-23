// 测试用例9: Channel通道通信
// 使用Channel进行线程间通信，无数据竞争

main() {
    let channel = Channel<Int64>()
    
    // 线程1: 发送数据
    spawn {
        channel.send(42)  // 发送操作
    }
    
    // 线程2: 接收数据
    spawn {
        let value = channel.receive()  // 接收操作
        println(value)
    }
}